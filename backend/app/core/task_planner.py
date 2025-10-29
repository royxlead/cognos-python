"""Task planner for decomposing complex queries into subtasks."""
import logging
import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set
from enum import Enum
from app.core.config import get_settings
from app.core.llm_manager import llm_manager

logger = logging.getLogger(__name__)
settings = get_settings()


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """Individual task in a plan."""
    id: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'description': self.description,
            'dependencies': self.dependencies,
            'status': self.status.value,
            'result': self.result,
            'error': self.error
        }


class TaskPlanner:
    """Plans and executes complex tasks by decomposition."""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
    
    async def decompose_task(self, query: str, context: str = "") -> List[Task]:
        """Break down complex query into subtasks."""
        decomposition_prompt = f"""You are a task planning AI. Break down the following complex query into simple, actionable subtasks.

{context}

Query: {query}

Provide a task decomposition in the following JSON format:
{{
  "tasks": [
    {{
      "id": "task_1",
      "description": "Clear description of what to do",
      "dependencies": []
    }},
    {{
      "id": "task_2",
      "description": "Another task",
      "dependencies": ["task_1"]
    }}
  ]
}}

Rules:
1. Each task should be simple and focused
2. List dependencies using task IDs
3. Tasks without dependencies can run in parallel
4. Order tasks logically

Generate the task decomposition:"""
        
        try:
            response = await llm_manager.generate(decomposition_prompt, temperature=0.5)
            
            # Parse JSON response
            tasks = self._parse_task_json(response)
            
            # Store tasks
            for task in tasks:
                self.tasks[task.id] = task
            
            logger.info(f"Decomposed query into {len(tasks)} tasks")
            return tasks
            
        except Exception as e:
            logger.error(f"Error decomposing task: {e}")
            # Fallback: create single task
            task = Task(id="task_1", description=query, dependencies=[])
            self.tasks[task.id] = task
            return [task]
    
    def _parse_task_json(self, response: str) -> List[Task]:
        """Parse task decomposition from JSON response."""
        try:
            # Extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1
            json_str = response[start:end]
            
            data = json.loads(json_str)
            
            tasks = []
            for task_data in data.get('tasks', []):
                task = Task(
                    id=task_data['id'],
                    description=task_data['description'],
                    dependencies=task_data.get('dependencies', [])
                )
                tasks.append(task)
            
            return tasks
            
        except Exception as e:
            logger.error(f"Error parsing task JSON: {e}")
            raise
    
    def get_executable_tasks(self) -> List[Task]:
        """Get tasks that are ready to execute (dependencies satisfied)."""
        executable = []
        
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            
            # Check if all dependencies are completed
            deps_satisfied = all(
                self.tasks.get(dep_id, Task(id=dep_id, description="")).status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
            )
            
            if deps_satisfied:
                executable.append(task)
        
        return executable
    
    async def execute_task(self, task: Task, context: str = "") -> str:
        """Execute a single task."""
        task.status = TaskStatus.IN_PROGRESS
        
        # Build context with dependency results
        dep_context = self._build_dependency_context(task)
        full_context = f"{context}\n\n{dep_context}" if dep_context else context
        
        execution_prompt = f"""Execute the following task:

{full_context}

Task: {task.description}

Provide a clear, concise result:"""
        
        try:
            result = await llm_manager.generate(execution_prompt, temperature=0.7)
            
            task.status = TaskStatus.COMPLETED
            task.result = result
            
            logger.info(f"Completed task {task.id}: {task.description[:50]}")
            return result
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            logger.error(f"Task {task.id} failed: {e}")
            raise
    
    def _build_dependency_context(self, task: Task) -> str:
        """Build context from completed dependency results."""
        if not task.dependencies:
            return ""
        
        context_parts = ["Results from previous tasks:"]
        
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if dep_task and dep_task.result:
                context_parts.append(f"\n{dep_id}: {dep_task.result}")
        
        return "\n".join(context_parts)
    
    async def execute_plan(self, context: str = "") -> Dict[str, Any]:
        """Execute all tasks in the plan respecting dependencies."""
        results = []
        
        while True:
            # Get tasks ready to execute
            executable = self.get_executable_tasks()
            
            if not executable:
                # Check if all tasks are completed
                all_completed = all(
                    task.status == TaskStatus.COMPLETED
                    for task in self.tasks.values()
                )
                
                if all_completed:
                    break
                else:
                    # Check for failures
                    failed_tasks = [
                        task for task in self.tasks.values()
                        if task.status == TaskStatus.FAILED
                    ]
                    if failed_tasks:
                        logger.error(f"Plan execution stopped due to {len(failed_tasks)} failed tasks")
                        break
                    else:
                        logger.warning("No executable tasks but not all completed - possible deadlock")
                        break
            
            # Execute tasks (could be parallelized in future)
            for task in executable:
                try:
                    result = await self.execute_task(task, context)
                    results.append({
                        'task_id': task.id,
                        'description': task.description,
                        'result': result
                    })
                except Exception as e:
                    logger.error(f"Error executing task {task.id}: {e}")
        
        # Compile final result
        final_result = self._compile_results(results)
        
        return {
            'tasks': [task.to_dict() for task in self.tasks.values()],
            'results': results,
            'final_result': final_result,
            'status': 'completed' if all(
                task.status == TaskStatus.COMPLETED for task in self.tasks.values()
            ) else 'partial'
        }
    
    def _compile_results(self, results: List[Dict[str, Any]]) -> str:
        """Compile individual task results into final answer."""
        if not results:
            return "No results available"
        
        compiled = ["Task Execution Results:\n"]
        
        for i, result in enumerate(results, 1):
            compiled.append(f"{i}. {result['description']}")
            compiled.append(f"   Result: {result['result']}\n")
        
        return "\n".join(compiled)
    
    def get_task_graph(self) -> Dict[str, Any]:
        """Get task dependency graph for visualization."""
        nodes = []
        edges = []
        
        for task in self.tasks.values():
            nodes.append({
                'id': task.id,
                'label': task.description[:50],
                'status': task.status.value
            })
            
            for dep_id in task.dependencies:
                edges.append({
                    'from': dep_id,
                    'to': task.id
                })
        
        return {
            'nodes': nodes,
            'edges': edges
        }
    
    def reset(self):
        """Reset planner state."""
        self.tasks = {}


# Global task planner instance
task_planner = TaskPlanner()

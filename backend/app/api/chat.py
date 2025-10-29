"""Chat API endpoints."""
import logging
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.schemas import ChatRequest, ChatResponse, ReasoningStep
from app.core.llm_manager import llm_manager
from app.core.memory_manager import memory_manager
from app.core.reasoning_engine import reasoning_engine
from app.core.context_manager import context_manager
from app.core.local_storage import local_storage

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """Main chat endpoint with memory and reasoning."""
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Ensure conversation exists for this session (avoid race with background tasks)
        if not local_storage.get_conversation(session_id):
            local_storage.create_conversation(session_id, model_used=None)

        # Add user message to short-term memory
        memory_manager.add_to_short_term("user", request.message)
        
        # Extract user information from message
        user_info = context_manager.extract_user_info(request.message)
        
        # Store user info as memories
        if user_info.get('preferences'):
            for key, value in user_info['preferences'].items():
                background_tasks.add_task(
                    memory_manager.add_memory,
                    content=f"User preference: {key} = {value}",
                    memory_type="preference",
                    importance=1.5,
                    session_id=session_id
                )
        
        if user_info.get('facts'):
            for fact in user_info['facts']:
                background_tasks.add_task(
                    memory_manager.add_memory,
                    content=f"User fact: {fact}",
                    memory_type="user_info",
                    importance=2.0,
                    session_id=session_id
                )
        
        # Get relevant context from memories
        context = await memory_manager.get_context(
            request.message,
            k=5,
            include_short_term=True
        )
        
        # Count memories used
        memories_used = len(await memory_manager.retrieve(request.message, k=5))
        
        # Build prompt
        full_prompt = context_manager.build_prompt(
            query=request.message,
            context=context
        )
        
        # Generate response with reasoning
        result = await reasoning_engine.reason(
            query=full_prompt,
            context=context,
            use_cot=request.enable_reasoning
        )
        
        # Add assistant response to short-term memory
        memory_manager.add_to_short_term("assistant", result['answer'])
        
        # Store conversation as memory
        background_tasks.add_task(
            memory_manager.add_memory,
            content=f"Q: {request.message}\nA: {result['answer']}",
            memory_type="conversation",
            importance=1.0,
            session_id=session_id
        )
        
        # Save messages to local storage
        background_tasks.add_task(
            local_storage.add_message,
            session_id=session_id,
            role="user",
            content=request.message,
            memories_used=0
        )
        background_tasks.add_task(
            local_storage.add_message,
            session_id=session_id,
            role="assistant",
            content=result['answer'],
            reasoning_steps=[step for step in result.get('reasoning_steps', [])],
            confidence=result.get('confidence'),
            memories_used=memories_used
        )
        
        # Convert reasoning steps to schema
        reasoning_steps = [
            ReasoningStep(**step) for step in result.get('reasoning_steps', [])
        ]
        
        return ChatResponse(
            answer=result['answer'],
            reasoning_steps=reasoning_steps,
            memories_used=memories_used,
            confidence=result.get('confidence', 0.8),
            method=result.get('method', 'direct'),
            session_id=session_id
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/task-plan")
async def chat_with_task_planning(request: ChatRequest):
    """Chat endpoint with task decomposition and planning."""
    try:
        from app.core.task_planner import task_planner
        
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Get context
        context = await memory_manager.get_context(request.message, k=5)
        
        # Decompose task
        tasks = await task_planner.decompose_task(request.message, context)
        
        # Execute task plan
        result = await task_planner.execute_plan(context)
        
        # Store result as memory
        await memory_manager.add_memory(
            content=f"Task plan for: {request.message}\nResult: {result['final_result']}",
            memory_type="conversation",
            importance=1.5,
            session_id=session_id
        )
        
        # Reset planner for next request
        task_planner.reset()
        
        return {
            "answer": result['final_result'],
            "task_plan": result,
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"Error in task planning: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

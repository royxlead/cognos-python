"""Reasoning engine with Chain-of-Thought and multi-step decomposition."""
import logging
import json
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from app.core.config import get_settings
from app.core.llm_manager import llm_manager

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ReasoningStep:
    """Single step in a reasoning chain."""
    step_number: int
    thought: str
    action: str
    observation: str
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'step_number': self.step_number,
            'thought': self.thought,
            'action': self.action,
            'observation': self.observation,
            'confidence': self.confidence
        }


class ReasoningEngine:
    """Engine for multi-step reasoning with Chain-of-Thought."""
    
    def __init__(self):
        self.max_steps = settings.MAX_REASONING_STEPS
        self.min_confidence = settings.MIN_CONFIDENCE_THRESHOLD
        self.enable_cot = settings.ENABLE_COT
    
    async def reason(
        self,
        query: str,
        context: str,
        use_cot: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Main reasoning method that chooses between direct and CoT reasoning."""
        use_cot = use_cot if use_cot is not None else self.enable_cot
        
        # Determine if query requires multi-step reasoning
        if use_cot and await self._requires_complex_reasoning(query):
            logger.info("Using Chain-of-Thought reasoning")
            return await self._chain_of_thought(query, context)
        else:
            logger.info("Using direct reasoning")
            return await self._direct_answer(query, context)
    
    async def _requires_complex_reasoning(self, query: str) -> bool:
        """Determine if query requires multi-step reasoning."""
        # Simple heuristics for now
        complexity_indicators = [
            "how can i", "steps to", "plan for", "analyze",
            "compare", "why", "explain", "multiple", "several"
        ]
        
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in complexity_indicators)
    
    async def _chain_of_thought(
        self,
        query: str,
        context: str
    ) -> Dict[str, Any]:
        """Execute multi-step Chain-of-Thought reasoning."""
        steps: List[ReasoningStep] = []
        
        # Build CoT prompt
        cot_prompt = self._build_cot_prompt(query, context)
        
        try:
            # Generate reasoning steps
            response = await llm_manager.generate(cot_prompt, temperature=0.7)
            
            # Parse reasoning steps from response
            parsed_steps = self._parse_reasoning_steps(response)
            steps.extend(parsed_steps)
            
            # Extract final answer
            final_answer = self._extract_final_answer(response)
            
            # Calculate overall confidence
            avg_confidence = sum(step.confidence for step in steps) / len(steps) if steps else 0.5
            
            # Self-reflection on answer quality
            reflection = await self.self_reflect(query, final_answer, steps)
            
            return {
                'answer': final_answer,
                'reasoning_steps': [step.to_dict() for step in steps],
                'confidence': avg_confidence,
                'reflection': reflection,
                'method': 'chain_of_thought'
            }
            
        except Exception as e:
            logger.error(f"Error in CoT reasoning: {e}")
            # Fallback to direct answer
            return await self._direct_answer(query, context)
    
    def _build_cot_prompt(self, query: str, context: str) -> str:
        """Build prompt for Chain-of-Thought reasoning."""
        prompt = f"""You are COGNOS, an advanced AI assistant with reasoning capabilities.

{context}

Task: Answer the following query using step-by-step reasoning.

For each reasoning step, provide:
1. **Thought**: What you're thinking about
2. **Action**: What action you're taking
3. **Observation**: What you discovered or concluded
4. **Confidence**: Your confidence level (0.0 to 1.0)

Format your response as follows:
STEP 1:
Thought: [your thought]
Action: [your action]
Observation: [your observation]
Confidence: [0.0-1.0]

STEP 2:
...

FINAL ANSWER:
[Your comprehensive answer based on the reasoning steps]

Query: {query}

Begin your step-by-step reasoning:"""
        
        return prompt
    
    def _parse_reasoning_steps(self, response: str) -> List[ReasoningStep]:
        """Parse reasoning steps from LLM response."""
        steps = []
        
        try:
            # Split by STEP markers
            parts = response.split('STEP ')
            
            for i, part in enumerate(parts[1:], 1):  # Skip first empty part
                if 'FINAL ANSWER' in part:
                    part = part.split('FINAL ANSWER')[0]
                
                # Extract components
                thought = self._extract_field(part, 'Thought')
                action = self._extract_field(part, 'Action')
                observation = self._extract_field(part, 'Observation')
                confidence_str = self._extract_field(part, 'Confidence')
                
                # Parse confidence
                try:
                    confidence = float(confidence_str)
                except (ValueError, TypeError):
                    confidence = 0.7  # Default confidence
                
                steps.append(ReasoningStep(
                    step_number=i,
                    thought=thought,
                    action=action,
                    observation=observation,
                    confidence=min(max(confidence, 0.0), 1.0)
                ))
                
        except Exception as e:
            logger.warning(f"Error parsing reasoning steps: {e}")
        
        return steps
    
    def _extract_field(self, text: str, field_name: str) -> str:
        """Extract a field value from text."""
        try:
            start_marker = f"{field_name}:"
            if start_marker in text:
                start = text.index(start_marker) + len(start_marker)
                # Find end (next field or newline)
                end_markers = ['\nThought:', '\nAction:', '\nObservation:', '\nConfidence:', '\nSTEP']
                end = len(text)
                for marker in end_markers:
                    if marker in text[start:]:
                        potential_end = text.index(marker, start)
                        end = min(end, potential_end)
                
                value = text[start:end].strip()
                return value
        except Exception as e:
            logger.warning(f"Error extracting field {field_name}: {e}")
        
        return ""
    
    def _extract_final_answer(self, response: str) -> str:
        """Extract final answer from CoT response."""
        if 'FINAL ANSWER:' in response:
            answer = response.split('FINAL ANSWER:')[-1].strip()
            return answer
        
        # Fallback: return last observation if no final answer
        steps = self._parse_reasoning_steps(response)
        if steps:
            return steps[-1].observation
        
        return response
    
    async def _direct_answer(self, query: str, context: str) -> Dict[str, Any]:
        """Generate direct answer without multi-step reasoning."""
        prompt = f"""You are COGNOS, a helpful AI assistant.

{context}

User Query: {query}

Provide a clear, comprehensive answer:"""
        
        try:
            answer = await llm_manager.generate(prompt, temperature=0.7)
            
            return {
                'answer': answer,
                'reasoning_steps': [],
                'confidence': 0.8,  # Default confidence for direct answers
                'reflection': None,
                'method': 'direct'
            }
            
        except Exception as e:
            logger.error(f"Error in direct answer: {e}")
            raise
    
    async def self_reflect(
        self,
        query: str,
        answer: str,
        steps: List[ReasoningStep]
    ) -> Dict[str, Any]:
        """Evaluate the quality and accuracy of the reasoning and answer."""
        reflection_prompt = f"""Evaluate the following reasoning process and answer:

Query: {query}

Reasoning Steps:
{self._format_steps_for_reflection(steps)}

Final Answer:
{answer}

Provide a brief evaluation covering:
1. Logical consistency of the reasoning
2. Completeness of the answer
3. Potential improvements
4. Overall quality score (0.0 to 1.0)

Format as:
Consistency: [evaluation]
Completeness: [evaluation]
Improvements: [suggestions]
Quality Score: [0.0-1.0]"""
        
        try:
            reflection_text = await llm_manager.generate(reflection_prompt, temperature=0.5)
            
            # Parse quality score
            quality_score = 0.8  # Default
            if 'Quality Score:' in reflection_text:
                try:
                    score_text = reflection_text.split('Quality Score:')[-1].strip().split()[0]
                    quality_score = float(score_text)
                except (ValueError, IndexError):
                    pass
            
            return {
                'evaluation': reflection_text,
                'quality_score': quality_score
            }
            
        except Exception as e:
            logger.error(f"Error in self-reflection: {e}")
            return {
                'evaluation': 'Reflection unavailable',
                'quality_score': 0.7
            }
    
    def _format_steps_for_reflection(self, steps: List[ReasoningStep]) -> str:
        """Format reasoning steps for reflection prompt."""
        formatted = []
        for step in steps:
            formatted.append(f"Step {step.step_number}:")
            formatted.append(f"  Thought: {step.thought}")
            formatted.append(f"  Action: {step.action}")
            formatted.append(f"  Observation: {step.observation}")
            formatted.append(f"  Confidence: {step.confidence}")
        
        return "\n".join(formatted)


# Global reasoning engine instance
reasoning_engine = ReasoningEngine()

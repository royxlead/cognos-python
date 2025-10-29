"""Conversation summarization for efficient context management."""
from typing import List, Dict, Optional
from app.core.llm_manager import llm_manager
from app.core.local_storage import local_storage
from app.core.logger import get_logger

logger = get_logger("summarizer")


class ConversationSummarizer:
    """Summarize long conversations to save context tokens."""
    
    def __init__(self, threshold: int = 20):
        """
        Initialize summarizer.
        
        Args:
            threshold: Message count threshold for auto-summarization
        """
        self.threshold = threshold
    
    async def summarize_conversation(
        self,
        messages: List[Dict],
        include_key_points: bool = True
    ) -> str:
        """
        Summarize a conversation.
        
        Args:
            messages: List of messages to summarize
            include_key_points: Whether to extract key points
            
        Returns:
            Concise summary of the conversation
        """
        if not messages:
            return ""
        
        # Build conversation text
        conversation_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in messages
        ])
        
        # Create summarization prompt
        prompt = f"""Summarize the following conversation concisely. Focus on:
1. Main topics discussed
2. Important information shared
3. User preferences or facts mentioned
4. Key decisions or conclusions

Conversation:
{conversation_text}

Summary:"""
        
        try:
            # Generate summary using LLM
            summary = await llm_manager.generate(prompt, max_tokens=500)
            
            logger.info(
                "Generated conversation summary",
                message_count=len(messages),
                summary_length=len(summary)
            )
            
            return summary
            
        except Exception as e:
            logger.error("Failed to summarize conversation", error=e)
            # Fallback: basic summary
            return self._basic_summary(messages)
    
    def _basic_summary(self, messages: List[Dict]) -> str:
        """
        Create basic summary without LLM.
        
        Args:
            messages: List of messages
            
        Returns:
            Basic summary
        """
        total_messages = len(messages)
        user_messages = [m for m in messages if m["role"] == "user"]
        assistant_messages = [m for m in messages if m["role"] == "assistant"]
        
        # Extract first and last messages
        first_topic = user_messages[0]["content"][:100] if user_messages else ""
        last_topic = user_messages[-1]["content"][:100] if user_messages else ""
        
        summary = f"""Conversation with {total_messages} messages 
({len(user_messages)} user, {len(assistant_messages)} assistant).
Started with: {first_topic}...
Last discussed: {last_topic}..."""
        
        return summary
    
    async def summarize_session(self, session_id: str) -> Optional[str]:
        """
        Summarize an entire conversation session.
        
        Args:
            session_id: Session ID to summarize
            
        Returns:
            Session summary or None if not found
        """
        conversation = local_storage.get_conversation(session_id)
        
        if not conversation:
            logger.warning(f"Conversation {session_id} not found")
            return None
        
        messages = conversation.get("messages", [])
        
        if not messages:
            return "Empty conversation"
        
        summary = await self.summarize_conversation(messages)
        
        # Update conversation with summary
        local_storage.update_conversation(session_id, {"summary": summary})
        
        return summary
    
    async def auto_summarize_if_needed(
        self,
        session_id: str,
        force: bool = False
    ) -> Optional[str]:
        """
        Automatically summarize if conversation exceeds threshold.
        
        Args:
            session_id: Session ID to check
            force: Force summarization regardless of threshold
            
        Returns:
            Summary if created, None otherwise
        """
        conversation = local_storage.get_conversation(session_id)
        
        if not conversation:
            return None
        
        messages = conversation.get("messages", [])
        message_count = len(messages)
        
        # Check if already summarized
        if conversation.get("summary") and not force:
            logger.debug(f"Conversation {session_id} already summarized")
            return conversation["summary"]
        
        # Check threshold
        if message_count < self.threshold and not force:
            logger.debug(
                f"Conversation {session_id} below threshold",
                count=message_count,
                threshold=self.threshold
            )
            return None
        
        # Summarize
        logger.info(f"Auto-summarizing conversation {session_id}")
        return await self.summarize_session(session_id)
    
    async def extract_key_points(self, messages: List[Dict]) -> List[str]:
        """
        Extract key points from conversation.
        
        Args:
            messages: List of messages
            
        Returns:
            List of key points
        """
        conversation_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in messages
        ])
        
        prompt = f"""Extract 3-5 key points from this conversation as bullet points:

{conversation_text}

Key Points:"""
        
        try:
            response = await llm_manager.generate(prompt, max_tokens=300)
            
            # Parse bullet points
            points = [
                line.strip().lstrip('•-*').strip()
                for line in response.split('\n')
                if line.strip() and (line.strip().startswith(('•', '-', '*', '1', '2', '3', '4', '5')))
            ]
            
            return points[:5]  # Max 5 points
            
        except Exception as e:
            logger.error("Failed to extract key points", error=e)
            return []
    
    async def get_context_summary(
        self,
        session_id: str,
        max_messages: int = 10
    ) -> str:
        """
        Get summarized context for a conversation.
        
        Args:
            session_id: Session ID
            max_messages: Number of recent messages to include
            
        Returns:
            Context string with summary and recent messages
        """
        conversation = local_storage.get_conversation(session_id)
        
        if not conversation:
            return ""
        
        summary = conversation.get("summary", "")
        messages = conversation.get("messages", [])
        
        # Get recent messages
        recent_messages = messages[-max_messages:]
        
        # Build context
        context_parts = []
        
        if summary:
            context_parts.append(f"[Previous Summary]\n{summary}\n")
        
        if recent_messages:
            context_parts.append("[Recent Messages]")
            for msg in recent_messages:
                context_parts.append(f"{msg['role'].upper()}: {msg['content']}")
        
        return "\n".join(context_parts)


# Global summarizer instance
summarizer = ConversationSummarizer()

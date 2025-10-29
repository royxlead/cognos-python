"""Context manager for optimizing token usage and building prompts."""
import logging
import re
from typing import List, Dict, Any, Optional
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ContextManager:
    """Manages context building and token optimization."""
    
    def __init__(self):
        self.max_tokens = settings.MAX_CONTEXT_TOKENS
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for COGNOS."""
        return """You are COGNOS, an advanced cognitive AI assistant with:
- Long-term memory: You remember past conversations and user preferences
- Reasoning capabilities: You can break down complex problems step-by-step
- Adaptive learning: You improve responses based on user interactions

Your responses should be:
- Clear and well-structured
- Informed by relevant memories and context
- Thoughtful and reasoned when appropriate
- Helpful and user-focused"""
    
    def build_prompt(
        self,
        query: str,
        context: str = "",
        user_profile: Optional[Dict[str, Any]] = None,
        system_context: Optional[str] = None
    ) -> str:
        """Build complete prompt with system instructions, context, and query."""
        prompt_parts = []
        
        # System instructions
        if system_context:
            prompt_parts.append(system_context)
        else:
            prompt_parts.append(self.system_prompt)
        
        # User profile
        if user_profile:
            profile_text = self._format_user_profile(user_profile)
            if profile_text:
                prompt_parts.append(f"\nUser Profile:\n{profile_text}")
        
        # Context (memories, conversation history)
        if context:
            optimized_context = self.optimize_context(context)
            prompt_parts.append(f"\n{optimized_context}")
        
        # Current query
        prompt_parts.append(f"\nCurrent Query: {query}")
        
        # Combine all parts
        full_prompt = "\n".join(prompt_parts)
        
        # Ensure we're within token limit
        full_prompt = self._trim_to_token_limit(full_prompt)
        
        return full_prompt
    
    def optimize_context(self, context: str, max_tokens: Optional[int] = None) -> str:
        """Optimize context to fit within token limits."""
        max_tokens = max_tokens or self.max_tokens
        
        # Rough token estimation (1 token ≈ 4 characters)
        estimated_tokens = len(context) / 4
        
        if estimated_tokens <= max_tokens:
            return context
        
        # Need to trim context
        logger.info(f"Context too large ({estimated_tokens:.0f} tokens), optimizing...")
        
        # Strategy: Keep most recent and most relevant parts
        sections = context.split('\n\n')
        
        # Prioritize sections
        prioritized = self._prioritize_sections(sections)
        
        # Build optimized context
        optimized = []
        current_tokens = 0
        
        for section, priority in prioritized:
            section_tokens = len(section) / 4
            if current_tokens + section_tokens <= max_tokens:
                optimized.append(section)
                current_tokens += section_tokens
            elif priority > 0.8:  # High priority, try to summarize
                summary = self._summarize_section(section)
                summary_tokens = len(summary) / 4
                if current_tokens + summary_tokens <= max_tokens:
                    optimized.append(f"[Summarized] {summary}")
                    current_tokens += summary_tokens
        
        return '\n\n'.join(optimized)
    
    def _prioritize_sections(self, sections: List[str]) -> List[tuple]:
        """Prioritize context sections by importance."""
        prioritized = []
        
        for section in sections:
            priority = 0.5  # Default priority
            
            # Boost priority for certain keywords
            if 'Recent Conversation' in section:
                priority = 1.0
            elif 'User Profile' in section:
                priority = 0.9
            elif 'Relevant Memories' in section:
                priority = 0.8
            elif section.startswith('[user_info]'):
                priority = 0.85
            elif section.startswith('[preference]'):
                priority = 0.75
            
            prioritized.append((section, priority))
        
        # Sort by priority (descending)
        prioritized.sort(key=lambda x: x[1], reverse=True)
        
        return prioritized
    
    def _summarize_section(self, section: str, max_length: int = 200) -> str:
        """Summarize a section to reduce token count."""
        if len(section) <= max_length:
            return section
        
        # Simple summarization: keep first and last sentences
        sentences = section.split('.')
        if len(sentences) <= 2:
            return section[:max_length] + "..."
        
        summary = sentences[0] + '. ... ' + sentences[-1]
        return summary[:max_length]
    
    def _trim_to_token_limit(self, text: str, max_tokens: Optional[int] = None) -> str:
        """Trim text to fit within token limit."""
        max_tokens = max_tokens or self.max_tokens
        
        # Rough token count (1 token ≈ 4 characters)
        max_chars = max_tokens * 4
        
        if len(text) <= max_chars:
            return text
        
        # Trim from the middle, keeping beginning and end
        keep_start = int(max_chars * 0.6)
        keep_end = int(max_chars * 0.3)
        
        trimmed = text[:keep_start] + "\n\n[... context trimmed ...]\n\n" + text[-keep_end:]
        
        return trimmed
    
    def _format_user_profile(self, profile: Dict[str, Any]) -> str:
        """Format user profile dictionary as text."""
        if not profile:
            return ""
        
        profile_parts = []
        
        # Extract key information
        if 'name' in profile:
            profile_parts.append(f"Name: {profile['name']}")
        
        if 'preferences' in profile and isinstance(profile['preferences'], dict):
            prefs = profile['preferences']
            if prefs:
                profile_parts.append("Preferences:")
                for key, value in prefs.items():
                    profile_parts.append(f"  - {key}: {value}")
        
        if 'facts' in profile and isinstance(profile['facts'], list):
            facts = profile['facts']
            if facts:
                profile_parts.append("Known facts:")
                for fact in facts[:5]:  # Limit to 5 facts
                    profile_parts.append(f"  - {fact}")
        
        return "\n".join(profile_parts)
    
    def extract_user_info(self, text: str) -> Dict[str, Any]:
        """Extract user information from conversation text."""
        user_info = {
            'preferences': {},
            'facts': [],
            'interests': []
        }
        
        # Pattern matching for common information
        text_lower = text.lower()
        
        # Preferences (I like/love/prefer X)
        pref_patterns = [
            r"i (?:like|love|prefer|enjoy) ([^,.!?]+)",
            r"my favorite ([^,.!?]+) (?:is|are) ([^,.!?]+)"
        ]
        
        for pattern in pref_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if isinstance(match, tuple):
                    user_info['preferences'][match[0]] = match[1]
                else:
                    user_info['preferences']['general'] = match
        
        # Facts (I am/I have/My X is Y)
        fact_patterns = [
            r"i am ([^,.!?]+)",
            r"i have ([^,.!?]+)",
            r"my ([^,.!?]+) (?:is|are) ([^,.!?]+)"
        ]
        
        for pattern in fact_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if isinstance(match, tuple):
                    user_info['facts'].append(f"{match[0]}: {match[1]}")
                else:
                    user_info['facts'].append(match)
        
        # Limit facts to avoid bloat
        user_info['facts'] = user_info['facts'][:10]
        
        return user_info if (user_info['preferences'] or user_info['facts']) else {}
    
    def summarize_conversation(self, messages: List[Dict[str, str]]) -> str:
        """Summarize a long conversation to reduce token count."""
        if len(messages) <= 6:  # Short enough, no summary needed
            return self._format_messages(messages)
        
        # Keep recent messages
        recent = messages[-6:]
        
        # Summarize older messages
        older = messages[:-6]
        
        summary_parts = [
            f"Previous conversation ({len(older)} messages):",
            "Topics discussed: " + self._extract_topics(older)
        ]
        
        # Add recent messages in full
        summary_parts.append("\nRecent conversation:")
        summary_parts.append(self._format_messages(recent))
        
        return "\n".join(summary_parts)
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format messages as conversation text."""
        formatted = []
        for msg in messages:
            role = msg.get('role', 'user').capitalize()
            content = msg.get('content', '')
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)
    
    def _extract_topics(self, messages: List[Dict[str, str]]) -> str:
        """Extract main topics from messages."""
        # Simple topic extraction: find common nouns/phrases
        all_text = " ".join(msg.get('content', '') for msg in messages)
        
        # Extract capitalized words (potential topics)
        words = all_text.split()
        topics = set()
        
        for word in words:
            # Simple heuristic: words longer than 4 chars
            cleaned = word.strip('.,!?;:')
            if len(cleaned) > 4 and not cleaned.isupper():
                topics.add(cleaned.lower())
        
        # Return first few topics
        return ", ".join(list(topics)[:5])
    
    def count_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        # Rough estimation: 1 token ≈ 4 characters
        return len(text) // 4


# Global context manager instance
context_manager = ContextManager()

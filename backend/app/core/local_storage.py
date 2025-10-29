"""Local JSON-based storage for privacy-focused data persistence."""
import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from pathlib import Path
import hashlib
import logging
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LocalStorage:
    """Privacy-focused local JSON storage for conversations and metadata."""
    
    def __init__(self, data_dir: str = "data"):
        """Initialize local storage."""
        self.data_dir = Path(data_dir)
        self.conversations_dir = self.data_dir / "conversations"
        self.users_dir = self.data_dir / "users"
        self.memory_metadata_file = self.data_dir / "memory_metadata.json"
        
        # Create directories
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        self.users_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize memory metadata file
        if not self.memory_metadata_file.exists():
            self._save_json(self.memory_metadata_file, [])
    
    def _save_json(self, filepath: Path, data: Any):
        """Save data to JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
    
    def _load_json(self, filepath: Path, default: Any = None) -> Any:
        """Load data from JSON file."""
        if not filepath.exists():
            return default or []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error(f"Error loading {filepath}, returning default")
            return default or []
    
    # ==================== Conversation Management ====================
    
    def create_conversation(
        self, 
        session_id: str, 
        title: Optional[str] = None,
        model_used: Optional[str] = None
    ) -> Dict:
        """Create a new conversation."""
        model_value = model_used or settings.GEMINI_MODEL
        conversation = {
            "session_id": session_id,
            "title": title or f"Conversation {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            "model_used": model_value,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "messages": []
        }
        
        filepath = self.conversations_dir / f"{session_id}.json"
        self._save_json(filepath, conversation)
        return conversation
    
    def get_conversation(self, session_id: str) -> Optional[Dict]:
        """Get conversation by session ID."""
        filepath = self.conversations_dir / f"{session_id}.json"
        return self._load_json(filepath, default=None)
    
    def update_conversation(self, session_id: str, updates: Dict):
        """Update conversation metadata."""
        conversation = self.get_conversation(session_id)
        if conversation:
            conversation.update(updates)
            conversation['updated_at'] = datetime.now(timezone.utc).isoformat()
            filepath = self.conversations_dir / f"{session_id}.json"
            self._save_json(filepath, conversation)
    
    def list_conversations(self, limit: int = 50) -> List[Dict]:
        """List all conversations (sorted by updated_at)."""
        conversations = []
        
        for filepath in self.conversations_dir.glob("*.json"):
            conversation = self._load_json(filepath)
            if conversation:
                # Include only metadata, not full messages
                conversations.append({
                    "session_id": conversation.get("session_id"),
                    "title": conversation.get("title"),
                    "model_used": conversation.get("model_used"),
                    "created_at": conversation.get("created_at"),
                    "updated_at": conversation.get("updated_at"),
                    "message_count": len(conversation.get("messages", []))
                })
        
        # Sort by updated_at descending
        conversations.sort(
            key=lambda x: x.get("updated_at", ""), 
            reverse=True
        )
        
        return conversations[:limit]
    
    def delete_conversation(self, session_id: str) -> bool:
        """Delete a conversation."""
        filepath = self.conversations_dir / f"{session_id}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False
    
    # ==================== Message Management ====================
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        reasoning_steps: Optional[List] = None,
        confidence: Optional[float] = None,
        memories_used: int = 0
    ) -> Dict:
        """Add a message to a conversation."""
        # Get or create conversation
        conversation = self.get_conversation(session_id)
        if not conversation:
            conversation = self.create_conversation(session_id)
        
        message = {
            "role": role,
            "content": content,
            "reasoning_steps": reasoning_steps,
            "confidence": confidence,
            "memories_used": memories_used,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        conversation["messages"].append(message)
        conversation["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        filepath = self.conversations_dir / f"{session_id}.json"
        self._save_json(filepath, conversation)
        
        return message
    
    def get_messages(
        self, 
        session_id: str, 
        limit: Optional[int] = None
    ) -> List[Dict]:
        """Get messages from a conversation."""
        conversation = self.get_conversation(session_id)
        if not conversation:
            return []
        
        messages = conversation.get("messages", [])
        if limit:
            return messages[-limit:]
        return messages
    
    def get_recent_messages(self, limit: int = 20) -> List[Dict]:
        """Get recent messages across all conversations."""
        all_messages = []
        
        for filepath in self.conversations_dir.glob("*.json"):
            conversation = self._load_json(filepath)
            if conversation:
                for msg in conversation.get("messages", []):
                    all_messages.append({
                        **msg,
                        "session_id": conversation["session_id"]
                    })
        
        # Sort by timestamp descending
        all_messages.sort(
            key=lambda x: x.get("timestamp", ""), 
            reverse=True
        )
        
        return all_messages[:limit]
    
    # ==================== Memory Metadata Management ====================
    
    def add_memory_metadata(
        self,
        content_hash: str,
        content_preview: str,
        memory_type: str,
        importance: float = 1.0,
        session_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Add memory metadata."""
        memories = self._load_json(self.memory_metadata_file, default=[])
        
        # Check if already exists
        for mem in memories:
            if mem.get("content_hash") == content_hash:
                # Update access count and timestamp
                mem["access_count"] = mem.get("access_count", 0) + 1
                mem["last_accessed"] = datetime.now(timezone.utc).isoformat()
                self._save_json(self.memory_metadata_file, memories)
                return mem
        
        # Create new memory metadata
        memory_meta = {
            "content_hash": content_hash,
            "content_preview": content_preview[:200],
            "memory_type": memory_type,
            "importance": importance,
            "access_count": 0,
            "session_id": session_id,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_accessed": datetime.now(timezone.utc).isoformat()
        }
        
        memories.append(memory_meta)
        self._save_json(self.memory_metadata_file, memories)
        
        return memory_meta
    
    def get_memory_metadata(self, content_hash: str) -> Optional[Dict]:
        """Get memory metadata by content hash."""
        memories = self._load_json(self.memory_metadata_file, default=[])
        for mem in memories:
            if mem.get("content_hash") == content_hash:
                return mem
        return None
    
    def update_memory_access(self, content_hash: str):
        """Update memory access count and timestamp."""
        memories = self._load_json(self.memory_metadata_file, default=[])
        for mem in memories:
            if mem.get("content_hash") == content_hash:
                mem["access_count"] = mem.get("access_count", 0) + 1
                mem["last_accessed"] = datetime.now(timezone.utc).isoformat()
                self._save_json(self.memory_metadata_file, memories)
                break
    
    def list_memory_metadata(
        self, 
        memory_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """List memory metadata with optional filtering."""
        memories = self._load_json(self.memory_metadata_file, default=[])
        
        if memory_type:
            memories = [
                m for m in memories 
                if m.get("memory_type") == memory_type
            ]
        
        # Sort by last accessed descending
        memories.sort(
            key=lambda x: x.get("last_accessed", ""), 
            reverse=True
        )
        
        return memories[:limit]
    
    def delete_memory_metadata(self, content_hash: str) -> bool:
        """Delete memory metadata."""
        memories = self._load_json(self.memory_metadata_file, default=[])
        original_len = len(memories)
        
        memories = [
            m for m in memories 
            if m.get("content_hash") != content_hash
        ]
        
        if len(memories) < original_len:
            self._save_json(self.memory_metadata_file, memories)
            return True
        return False
    
    def get_memory_stats(self) -> Dict:
        """Get statistics about stored memories."""
        memories = self._load_json(self.memory_metadata_file, default=[])
        
        stats = {
            "total_memories": len(memories),
            "by_type": {},
            "total_accesses": sum(m.get("access_count", 0) for m in memories),
            "avg_importance": 0.0
        }
        
        if memories:
            # Count by type
            for mem in memories:
                mem_type = mem.get("memory_type", "unknown")
                stats["by_type"][mem_type] = stats["by_type"].get(mem_type, 0) + 1
            
            # Average importance
            stats["avg_importance"] = sum(
                m.get("importance", 1.0) for m in memories
            ) / len(memories)
        
        return stats
    
    # ==================== User Profile Management ====================
    
    def save_user_profile(
        self,
        user_id: str,
        name: Optional[str] = None,
        preferences: Optional[Dict] = None,
        facts: Optional[List] = None,
        interests: Optional[List] = None
    ) -> Dict:
        """Save or update user profile."""
        filepath = self.users_dir / f"{user_id}.json"
        
        profile = self._load_json(filepath, default={
            "user_id": user_id,
            "name": name,
            "preferences": {},
            "facts": [],
            "interests": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Update fields if provided
        if name is not None:
            profile["name"] = name
        if preferences is not None:
            profile["preferences"].update(preferences)
        if facts is not None:
            profile["facts"] = list(set(profile.get("facts", []) + facts))
        if interests is not None:
            profile["interests"] = list(set(profile.get("interests", []) + interests))

        profile["updated_at"] = datetime.now(timezone.utc).isoformat()

        self._save_json(filepath, profile)
        return profile
    
    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile."""
        filepath = self.users_dir / f"{user_id}.json"
        return self._load_json(filepath, default=None)
    
    # ==================== Utility Methods ====================
    
    def export_all_data(self, export_dir: Optional[str] = None) -> str:
        """Export all data to a timestamped directory."""
        if export_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_dir = self.data_dir / f"export_{timestamp}"
        
        export_path = Path(export_dir)
        export_path.mkdir(parents=True, exist_ok=True)
        
        # Copy all conversations
        conversations_export = export_path / "conversations"
        conversations_export.mkdir(exist_ok=True)
        for conv_file in self.conversations_dir.glob("*.json"):
            content = self._load_json(conv_file)
            self._save_json(conversations_export / conv_file.name, content)
        
        # Copy memory metadata
        memories = self._load_json(self.memory_metadata_file)
        self._save_json(export_path / "memory_metadata.json", memories)
        
        # Copy user profiles
        users_export = export_path / "users"
        users_export.mkdir(exist_ok=True)
        for user_file in self.users_dir.glob("*.json"):
            content = self._load_json(user_file)
            self._save_json(users_export / user_file.name, content)
        
        logger.info(f"Data exported to: {export_path}")
        return str(export_path)
    
    def get_storage_stats(self) -> Dict:
        """Get statistics about local storage."""
        conversation_count = len(list(self.conversations_dir.glob("*.json")))
        user_count = len(list(self.users_dir.glob("*.json")))
        
        # Calculate total size
        total_size = 0
        for file_path in self.data_dir.rglob("*.json"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        
        return {
            "conversations": conversation_count,
            "users": user_count,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "data_directory": str(self.data_dir.absolute())
        }


# Global instance
local_storage = LocalStorage()

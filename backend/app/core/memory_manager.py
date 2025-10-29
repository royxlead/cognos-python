"""Memory manager with FAISS vector database and importance scoring."""
import logging
import pickle
import os
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
import numpy as np
import faiss
from app.core.config import get_settings
from app.core.llm_manager import llm_manager
from app.core.local_storage import local_storage

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class Memory:
    """Individual memory with content, embedding, and metadata."""
    content: str
    embedding: np.ndarray
    memory_type: str  # 'user_info', 'conversation', 'knowledge', 'preference'
    importance: float = 1.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert memory to dictionary for serialization."""
        return {
            'content': self.content,
            'embedding': self.embedding.tolist() if isinstance(self.embedding, np.ndarray) else self.embedding,
            'memory_type': self.memory_type,
            'importance': self.importance,
            'timestamp': self.timestamp.isoformat(),
            'access_count': self.access_count,
            'session_id': self.session_id,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Memory':
        """Create memory from dictionary."""
        data['embedding'] = np.array(data['embedding'], dtype=np.float32)
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class MemoryManager:
    """Manages short-term and long-term memory with FAISS vector search."""
    
    def __init__(self):
        self.vector_dim = settings.VECTOR_DIM
        self.max_memories = settings.MAX_MEMORIES
        self.decay_days = settings.MEMORY_DECAY_DAYS
        
        # FAISS index for semantic search
        self.index = faiss.IndexFlatL2(self.vector_dim)
        
        # Memory storage
        self.memories: List[Memory] = []
        
        # Short-term memory (recent conversation)
        self.short_term: List[Dict[str, str]] = []
        self.short_term_max = settings.SHORT_TERM_MEMORY_SIZE
        
        # Load existing memories if available
        self.load()
    
    async def add_memory(
        self,
        content: str,
        memory_type: str,
        importance: float = 1.0,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None
    ) -> Optional[Memory]:
        """Add a new memory to the system."""
        try:
            # Generate embedding if not provided
            if embedding is None:
                embedding = await llm_manager.generate_embedding(content)
            
            # Convert to numpy array
            embedding_array = np.array(embedding, dtype=np.float32)
            
            # Create memory object
            memory = Memory(
                content=content,
                embedding=embedding_array,
                memory_type=memory_type,
                importance=importance,
                session_id=session_id,
                metadata=metadata or {}
            )
            
            # Add to FAISS index
            self.index.add(np.array([embedding_array]))
            
            # Add to memory list
            self.memories.append(memory)
            
            # Save metadata to local storage
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            local_storage.add_memory_metadata(
                content_hash=content_hash,
                content_preview=content,
                memory_type=memory_type,
                importance=importance,
                session_id=session_id,
                metadata=metadata
            )
            
            # Prune if exceeding max memories
            if len(self.memories) > self.max_memories:
                self._prune_memories()
            
            logger.info(f"Added memory: {memory_type} - {content[:50]}...")
            return memory
            
        except Exception as e:
            # Swallow embedding/indexing errors to avoid breaking API responses
            logger.warning(
                "Skipping memory indexing due to error while adding memory: %s",
                e,
            )
            return None
    
    async def retrieve(
        self,
        query: str,
        k: int = 5,
        memory_type: Optional[str] = None,
        session_id: Optional[str] = None,
        embedding: Optional[List[float]] = None
    ) -> List[Memory]:
        """Retrieve relevant memories using semantic search."""
        if len(self.memories) == 0:
            return []
        
        try:
            # Generate query embedding if not provided
            if embedding is None:
                embedding = await llm_manager.generate_embedding(query)
            
            query_embedding = np.array([embedding], dtype=np.float32)
            
            # Search FAISS index
            k_search = min(k * 4, len(self.memories))  # Get more candidates for filtering
            distances, indices = self.index.search(query_embedding, k_search)
            
            # Get candidate memories
            candidates = []
            for idx, distance in zip(indices[0], distances[0]):
                if idx < len(self.memories):
                    memory = self.memories[idx]
                    
                    # Apply filters
                    if memory_type and memory.memory_type != memory_type:
                        continue
                    if session_id and memory.session_id != session_id:
                        continue
                    
                    # Calculate relevance score
                    similarity = 1 / (1 + distance)  # Convert distance to similarity
                    relevance = self._calculate_relevance(memory, similarity)
                    
                    candidates.append((memory, relevance))
            
            # Sort by relevance and return top k
            candidates.sort(key=lambda x: x[1], reverse=True)
            top_memories = [mem for mem, _ in candidates[:k]]
            
            # Increment access count
            for memory in top_memories:
                memory.access_count += 1
            
            return top_memories
            
        except Exception as e:
            logger.error(f"Error retrieving memories: {e}")
            return []
    
    def _calculate_relevance(self, memory: Memory, similarity: float) -> float:
        """Calculate memory relevance score based on multiple factors."""
        # Time decay factor
        age_days = (datetime.now(timezone.utc) - memory.timestamp).days
        decay_factor = np.exp(-age_days / self.decay_days)
        
        # Access frequency factor
        access_factor = 1 + (memory.access_count / 10)
        
        # Combined score
        relevance = similarity * memory.importance * decay_factor * access_factor
        
        return relevance
    
    def add_to_short_term(self, role: str, content: str):
        """Add message to short-term memory (recent conversation)."""
        self.short_term.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Keep only recent messages
        if len(self.short_term) > self.short_term_max * 2:  # 2 messages per turn
            self.short_term = self.short_term[-self.short_term_max * 2:]
    
    def get_short_term_context(self) -> str:
        """Get recent conversation context as formatted string."""
        if not self.short_term:
            return ""
        
        context = "\n".join([
            f"{msg['role'].capitalize()}: {msg['content']}"
            for msg in self.short_term[-self.short_term_max * 2:]
        ])
        
        return f"Recent Conversation:\n{context}"
    
    async def get_context(
        self,
        query: str,
        k: int = 5,
        include_short_term: bool = True
    ) -> str:
        """Build context string from relevant memories."""
        context_parts = []
        
        # Add short-term context
        if include_short_term:
            short_term_context = self.get_short_term_context()
            if short_term_context:
                context_parts.append(short_term_context)
        
        # Retrieve and add relevant long-term memories
        memories = await self.retrieve(query, k=k)
        
        if memories:
            memory_context = "\n\nRelevant Memories:\n"
            for i, mem in enumerate(memories, 1):
                memory_context += f"{i}. [{mem.memory_type}] {mem.content}\n"
            context_parts.append(memory_context)
        
        return "\n\n".join(context_parts)
    
    def _prune_memories(self):
        """Remove least relevant memories when limit exceeded."""
        if len(self.memories) <= self.max_memories:
            return
        
        # Calculate relevance scores for all memories
        scores = []
        for memory in self.memories:
            relevance = self._calculate_relevance(memory, similarity=1.0)
            scores.append(relevance)
        
        # Get indices to keep (top max_memories)
        keep_indices = np.argsort(scores)[-self.max_memories:]
        
        # Rebuild index and memory list
        new_memories = [self.memories[i] for i in sorted(keep_indices)]
        new_embeddings = np.array([mem.embedding for mem in new_memories], dtype=np.float32)
        
        # Create new FAISS index
        self.index = faiss.IndexFlatL2(self.vector_dim)
        self.index.add(new_embeddings)
        
        self.memories = new_memories
        
        logger.info(f"Pruned memories: kept {len(self.memories)}/{len(scores)}")
    
    def save(self):
        """Save memories to disk."""
        try:
            # Save FAISS index
            faiss.write_index(self.index, settings.MEMORY_INDEX_PATH)
            
            # Save memory metadata
            memory_data = [mem.to_dict() for mem in self.memories]
            with open(settings.MEMORY_METADATA_PATH, 'wb') as f:
                pickle.dump(memory_data, f)
            
            logger.info(f"Saved {len(self.memories)} memories to disk")
            
        except Exception as e:
            logger.error(f"Error saving memories: {e}")
    
    def load(self):
        """Load memories from disk."""
        try:
            if os.path.exists(settings.MEMORY_INDEX_PATH) and os.path.exists(settings.MEMORY_METADATA_PATH):
                # Load FAISS index
                self.index = faiss.read_index(settings.MEMORY_INDEX_PATH)
                
                # Load memory metadata
                with open(settings.MEMORY_METADATA_PATH, 'rb') as f:
                    memory_data = pickle.load(f)
                
                self.memories = [Memory.from_dict(data) for data in memory_data]
                
                logger.info(f"Loaded {len(self.memories)} memories from disk")
            else:
                logger.info("No existing memories found")
                
        except Exception as e:
            logger.error(f"Error loading memories: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        if not self.memories:
            return {
                "total_memories": 0,
                "by_type": {},
                "avg_age_days": 0,
                "oldest_memory": None,
                "newest_memory": None
            }
        
        # Count by type
        type_counts = {}
        for mem in self.memories:
            type_counts[mem.memory_type] = type_counts.get(mem.memory_type, 0) + 1
        
        # Age statistics
        ages = [(datetime.now(timezone.utc) - mem.timestamp).days for mem in self.memories]
        
        return {
            "total_memories": len(self.memories),
            "by_type": type_counts,
            "avg_age_days": sum(ages) / len(ages),
            "oldest_memory": max(self.memories, key=lambda m: m.timestamp).timestamp.isoformat(),
            "newest_memory": min(self.memories, key=lambda m: m.timestamp).timestamp.isoformat(),
        }
    
    def clear(self):
        """Clear all memories."""
        self.index = faiss.IndexFlatL2(self.vector_dim)
        self.memories = []
        self.short_term = []
        logger.info("Cleared all memories")


# Global memory manager instance
memory_manager = MemoryManager()

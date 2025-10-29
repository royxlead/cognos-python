"""Memory API endpoints."""
import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from app.models.schemas import (
    MemoryCreate, MemoryResponse, MemorySearchRequest,
    MemoryStats
)
from app.core.memory_manager import memory_manager
from app.core.local_storage import local_storage

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[MemoryResponse])
async def list_memories(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    memory_type: Optional[str] = None
):
    """List all memories with pagination."""
    try:
        memories = memory_manager.memories
        
        # Filter by type if specified
        if memory_type:
            memories = [m for m in memories if m.memory_type == memory_type]
        
        # Paginate
        total = len(memories)
        memories = memories[skip:skip + limit]
        
        # Convert to response model
        return [
            MemoryResponse(
                content=m.content,
                memory_type=m.memory_type,
                importance=m.importance,
                timestamp=m.timestamp,
                access_count=m.access_count,
                session_id=m.session_id,
                metadata=m.metadata
            )
            for m in memories
        ]
        
    except Exception as e:
        logger.error(f"Error listing memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=MemoryResponse)
async def create_memory(memory: MemoryCreate):
    """Create a new memory."""
    try:
        new_memory = await memory_manager.add_memory(
            content=memory.content,
            memory_type=memory.memory_type,
            importance=memory.importance,
            session_id=memory.session_id,
            metadata=memory.metadata
        )
        if not new_memory:
            raise HTTPException(status_code=503, detail="Unable to create memory embedding at this time")
        
        return MemoryResponse(
            content=new_memory.content,
            memory_type=new_memory.memory_type,
            importance=new_memory.importance,
            timestamp=new_memory.timestamp,
            access_count=new_memory.access_count,
            session_id=new_memory.session_id,
            metadata=new_memory.metadata
        )
        
    except Exception as e:
        logger.error(f"Error creating memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=List[MemoryResponse])
async def search_memories(request: MemorySearchRequest):
    """Search memories by semantic similarity."""
    try:
        memories = await memory_manager.retrieve(
            query=request.query,
            k=request.k,
            memory_type=request.memory_type,
            session_id=request.session_id
        )
        
        return [
            MemoryResponse(
                content=m.content,
                memory_type=m.memory_type,
                importance=m.importance,
                timestamp=m.timestamp,
                access_count=m.access_count,
                session_id=m.session_id,
                metadata=m.metadata
            )
            for m in memories
        ]
        
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=MemoryStats)
async def get_memory_stats():
    """Get memory statistics."""
    try:
        stats = memory_manager.get_stats()
        
        # Add local storage stats
        storage_stats = local_storage.get_storage_stats()
        memory_metadata_stats = local_storage.get_memory_stats()
        
        stats['storage'] = storage_stats
        stats['metadata'] = memory_metadata_stats
        
        return MemoryStats(**stats)
        
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{memory_index}")
async def delete_memory(memory_index: int):
    """Delete a specific memory by index."""
    try:
        if memory_index < 0 or memory_index >= len(memory_manager.memories):
            raise HTTPException(status_code=404, detail="Memory not found")
        
        deleted_memory = memory_manager.memories.pop(memory_index)
        
        # Delete from local storage metadata
        import hashlib
        content_hash = hashlib.sha256(deleted_memory.content.encode()).hexdigest()
        local_storage.delete_memory_metadata(content_hash)
        
        # Rebuild FAISS index
        if memory_manager.memories:
            import numpy as np
            import faiss
            
            embeddings = np.array(
                [m.embedding for m in memory_manager.memories],
                dtype=np.float32
            )
            memory_manager.index = faiss.IndexFlatL2(memory_manager.vector_dim)
            memory_manager.index.add(embeddings)
        else:
            import faiss
            memory_manager.index = faiss.IndexFlatL2(memory_manager.vector_dim)
        
        # Save changes
        memory_manager.save()
        
        return {
            "status": "deleted",
            "memory": deleted_memory.content[:100]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/")
async def clear_all_memories():
    """Clear all memories."""
    try:
        count = len(memory_manager.memories)
        memory_manager.clear()
        memory_manager.save()
        
        return {
            "status": "cleared",
            "count": count
        }
        
    except Exception as e:
        logger.error(f"Error clearing memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def export_memories():
    """Export all memories as JSON."""
    try:
        memories_data = [m.to_dict() for m in memory_manager.memories]
        
        return {
            "memories": memories_data,
            "count": len(memories_data),
            "exported_at": "2025-10-28T00:00:00Z"
        }
        
    except Exception as e:
        logger.error(f"Error exporting memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

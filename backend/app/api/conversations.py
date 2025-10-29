"""Conversation history API endpoints for local storage."""
import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from app.core.local_storage import local_storage

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=100)
):
    """List all conversations."""
    try:
        conversations = local_storage.list_conversations(limit=limit)
        return {
            "conversations": conversations,
            "count": len(conversations)
        }
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}")
async def get_conversation(session_id: str):
    """Get a specific conversation with all messages."""
    try:
        conversation = local_storage.get_conversation(session_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/messages")
async def get_messages(
    session_id: str,
    limit: Optional[int] = None
):
    """Get messages from a conversation."""
    try:
        messages = local_storage.get_messages(session_id, limit=limit)
        return {
            "session_id": session_id,
            "messages": messages,
            "count": len(messages)
        }
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def delete_conversation(session_id: str):
    """Delete a conversation."""
    try:
        success = local_storage.delete_conversation(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {
            "status": "deleted",
            "session_id": session_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent/messages")
async def get_recent_messages(
    limit: int = Query(default=20, ge=1, le=100)
):
    """Get recent messages across all conversations."""
    try:
        messages = local_storage.get_recent_messages(limit=limit)
        return {
            "messages": messages,
            "count": len(messages)
        }
    except Exception as e:
        logger.error(f"Error getting recent messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def export_all_conversations():
    """Export all conversations and data."""
    try:
        export_path = local_storage.export_all_data()
        storage_stats = local_storage.get_storage_stats()
        
        return {
            "status": "exported",
            "export_path": export_path,
            "stats": storage_stats
        }
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storage/stats")
async def get_storage_stats():
    """Get local storage statistics."""
    try:
        storage_stats = local_storage.get_storage_stats()
        memory_stats = local_storage.get_memory_stats()
        
        return {
            "storage": storage_stats,
            "memory": memory_stats
        }
    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

"""API endpoints for cache management."""
from fastapi import APIRouter, HTTPException
from app.core.cache import cache
from app.core.logger import get_logger

router = APIRouter(prefix="/cache", tags=["cache"])
logger = get_logger("cache_api")


@router.get("/stats")
async def get_cache_stats():
    """Get cache statistics."""
    try:
        stats = cache.get_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error("Failed to get cache stats", error=e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_expired_cache():
    """Clean up expired cache entries."""
    try:
        deleted_count = cache.cleanup_expired()
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Cleaned up {deleted_count} expired cache entries"
        }
    except Exception as e:
        logger.error("Failed to cleanup cache", error=e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_cache():
    """Clear all cache entries."""
    try:
        deleted_count = cache.clear()
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Cleared {deleted_count} cache entries"
        }
    except Exception as e:
        logger.error("Failed to clear cache", error=e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{key}")
async def delete_cache_entry(key: str):
    """Delete a specific cache entry."""
    try:
        deleted = cache.delete(key)
        if not deleted:
            raise HTTPException(status_code=404, detail="Cache entry not found")
        
        return {
            "success": True,
            "message": f"Cache entry deleted: {key}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete cache entry: {key}", error=e)
        raise HTTPException(status_code=500, detail=str(e))

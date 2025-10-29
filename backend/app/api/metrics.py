"""Metrics API endpoints for monitoring."""
import logging
from fastapi import APIRouter, Query
from app.core.metrics import metrics_collector
from app.core.logger import get_logger

logger = get_logger("metrics_api")
router = APIRouter()


@router.get("/summary")
async def get_metrics_summary(hours: int = Query(default=24, ge=1, le=168)):
    """
    Get comprehensive metrics summary.
    
    Args:
        hours: Number of hours to analyze (1-168)
    
    Returns:
        Comprehensive metrics summary
    """
    try:
        summary = metrics_collector.get_summary(hours=hours)
        return summary
    except Exception as e:
        logger.error("Error getting metrics summary", error=e)
        return {"error": str(e)}


@router.get("/api")
async def get_api_metrics(hours: int = Query(default=24, ge=1, le=168)):
    """
    Get API request metrics.
    
    Args:
        hours: Number of hours to analyze
        
    Returns:
        API metrics including request counts, durations, error rates
    """
    try:
        stats = metrics_collector.get_api_stats(hours=hours)
        return stats
    except Exception as e:
        logger.error("Error getting API metrics", error=e)
        return {"error": str(e)}


@router.get("/llm")
async def get_llm_metrics(hours: int = Query(default=24, ge=1, le=168)):
    """
    Get LLM usage metrics.
    
    Args:
        hours: Number of hours to analyze
        
    Returns:
        LLM metrics including tokens, costs, model usage
    """
    try:
        stats = metrics_collector.get_llm_stats(hours=hours)
        return stats
    except Exception as e:
        logger.error("Error getting LLM metrics", error=e)
        return {"error": str(e)}


@router.get("/errors")
async def get_error_metrics(hours: int = Query(default=24, ge=1, le=168)):
    """
    Get error metrics.
    
    Args:
        hours: Number of hours to analyze
        
    Returns:
        Error metrics by type, severity, endpoint
    """
    try:
        stats = metrics_collector.get_error_stats(hours=hours)
        return stats
    except Exception as e:
        logger.error("Error getting error metrics", error=e)
        return {"error": str(e)}


@router.get("/memory")
async def get_memory_metrics(hours: int = Query(default=24, ge=1, le=168)):
    """
    Get memory operation metrics.
    
    Args:
        hours: Number of hours to analyze
        
    Returns:
        Memory operation metrics
    """
    try:
        stats = metrics_collector.get_memory_stats(hours=hours)
        return stats
    except Exception as e:
        logger.error("Error getting memory metrics", error=e)
        return {"error": str(e)}


@router.post("/cleanup")
async def cleanup_old_metrics(days_to_keep: int = Query(default=30, ge=7, le=365)):
    """
    Clean up old metrics files.
    
    Args:
        days_to_keep: Number of days to keep (7-365)
        
    Returns:
        Number of files deleted
    """
    try:
        deleted = metrics_collector.cleanup_old_metrics(days_to_keep=days_to_keep)
        return {
            "status": "success",
            "deleted_files": deleted,
            "message": f"Deleted {deleted} old metrics files"
        }
    except Exception as e:
        logger.error("Error cleaning up metrics", error=e)
        return {"error": str(e)}

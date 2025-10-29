"""Enhanced health check endpoints."""
from fastapi import APIRouter, status
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import psutil
import sys
from app.core.local_storage import LocalStorage
from app.core.cache import cache
from app.core.metrics import metrics_collector
from app.core.logger import get_logger

router = APIRouter(prefix="/health", tags=["health"])
logger = get_logger("health")

START_TIME = datetime.now()


def check_storage_health() -> Dict[str, Any]:
    """Check local storage health."""
    try:
        storage = LocalStorage()
        storage.get_all_conversations()
        
        storage_dir = Path(storage.storage_dir)
        writable = storage_dir.exists() and storage_dir.is_dir()
        
        return {
            "status": "healthy" if writable else "degraded",
            "storage_dir": str(storage_dir.absolute()),
            "writable": writable
        }
    except Exception as e:
        logger.error("Storage health check failed", error=e)
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def check_cache_health() -> Dict[str, Any]:
    """Check cache health."""
    try:
        stats = cache.get_stats()
        
        cache_dir = Path(cache.cache_dir)
        healthy = cache_dir.exists() and cache_dir.is_dir()
        
        return {
            "status": "healthy" if healthy else "degraded",
            "cache_dir": str(cache_dir.absolute()),
            "total_entries": stats["total_entries"],
            "total_size_mb": stats["total_size_mb"]
        }
    except Exception as e:
        logger.error("Cache health check failed", error=e)
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def check_system_health() -> Dict[str, Any]:
    """Check system resources."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('.')
        
        status = "healthy"
        if memory.percent > 90 or disk.percent > 90:
            status = "degraded"
        if memory.percent > 95 or disk.percent > 95:
            status = "critical"
        
        return {
            "status": status,
            "cpu_percent": round(cpu_percent, 2),
            "memory_percent": round(memory.percent, 2),
            "memory_available_mb": round(memory.available / (1024 * 1024), 2),
            "disk_percent": round(disk.percent, 2),
            "disk_free_gb": round(disk.free / (1024 * 1024 * 1024), 2)
        }
    except Exception as e:
        logger.error("System health check failed", error=e)
        return {
            "status": "unknown",
            "error": str(e)
        }


@router.get("", status_code=status.HTTP_200_OK)
@router.get("/", status_code=status.HTTP_200_OK)
async def basic_health():
    """Basic health check."""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness check.
    """
    storage_health = check_storage_health()
    cache_health = check_cache_health()
    
    is_ready = storage_health["status"] == "healthy"
    
    return {
        "ready": is_ready,
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "storage": storage_health,
            "cache": cache_health
        }
    }


@router.get("/live")
async def liveness_check():
    """
    Liveness check.
    """
    uptime_seconds = (datetime.now() - START_TIME).total_seconds()
    
    return {
        "alive": True,
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": round(uptime_seconds, 2),
        "python_version": sys.version
    }


@router.get("/detailed")
async def detailed_health():
    """Detailed health check with all components and metrics."""
    storage_health = check_storage_health()
    cache_health = check_cache_health()
    system_health = check_system_health()
    
    try:
        metrics_summary = metrics_collector.get_summary(hours=1)
    except Exception as e:
        logger.error("Failed to get metrics summary", error=e)
        metrics_summary = {"error": str(e)}
    
    statuses = [
        storage_health["status"],
        cache_health["status"],
        system_health["status"]
    ]
    
    if "unhealthy" in statuses or "critical" in statuses:
        overall_status = "unhealthy"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif "degraded" in statuses:
        overall_status = "degraded"
        status_code = status.HTTP_200_OK
    else:
        overall_status = "healthy"
        status_code = status.HTTP_200_OK
    
    uptime_seconds = (datetime.now() - START_TIME).total_seconds()
    
    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": round(uptime_seconds, 2),
        "components": {
            "storage": storage_health,
            "cache": cache_health,
            "system": system_health
        },
        "metrics_summary": metrics_summary
    }

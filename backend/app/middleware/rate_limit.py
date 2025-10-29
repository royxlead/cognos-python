"""File-based rate limiting middleware for privacy."""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logger import get_logger

logger = get_logger("rate_limit")


class RateLimiter:
    """Privacy-first file-based rate limiter."""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        storage_file: str = "data/rate_limits.json"
    ):
        """Initialize rate limiter."""
        self.rpm = requests_per_minute
        self.rph = requests_per_hour
        self.storage_file = Path(storage_file)
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.requests: Dict[str, list] = self._load()
        self.last_save = datetime.now()
    
    def _load(self) -> Dict[str, list]:
        """Load rate limit data from file."""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    return {
                        ip: [datetime.fromisoformat(ts) for ts in timestamps]
                        for ip, timestamps in data.items()
                    }
            except (json.JSONDecodeError, ValueError) as e:
                logger.error("Failed to load rate limit data", error=e)
                return {}
        return {}
    
    def _save(self):
        """Save rate limit data to file."""
        try:
            data = {
                ip: [ts.isoformat() for ts in timestamps]
                for ip, timestamps in self.requests.items()
            }
            
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.last_save = datetime.now()
        except Exception as e:
            logger.error("Failed to save rate limit data", error=e)
    
    def _cleanup_old_requests(self, ip: str, now: datetime):
        """Remove requests older than 1 hour."""
        if ip in self.requests:
            cutoff = now - timedelta(hours=1)
            self.requests[ip] = [
                ts for ts in self.requests[ip]
                if ts > cutoff
            ]
            
            if not self.requests[ip]:
                del self.requests[ip]
    
    def _save_periodically(self):
        """Save to file every 5 minutes."""
        if (datetime.now() - self.last_save).total_seconds() > 300:
            self._save()
    
    def check_rate_limit(
        self,
        client_ip: str,
        endpoint: Optional[str] = None
    ) -> tuple[bool, Dict[str, int]]:
        """Check if request should be rate limited."""
        now = datetime.now()
        
        self._cleanup_old_requests(client_ip, now)
        
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        recent_requests = self.requests[client_ip]
        
        one_minute_ago = now - timedelta(minutes=1)
        recent_minute = [ts for ts in recent_requests if ts > one_minute_ago]
        
        if len(recent_minute) >= self.rpm:
            logger.warning(
                "Rate limit exceeded (per minute)",
                client_ip=client_ip,
                requests=len(recent_minute),
                limit=self.rpm
            )
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": f"{self.rpm} requests per minute",
                    "retry_after": 60 - (now - recent_minute[0]).seconds
                },
                headers={"Retry-After": "60"}
            )
        
        one_hour_ago = now - timedelta(hours=1)
        recent_hour = [ts for ts in recent_requests if ts > one_hour_ago]
        
        if len(recent_hour) >= self.rph:
            logger.warning(
                "Rate limit exceeded (per hour)",
                client_ip=client_ip,
                requests=len(recent_hour),
                limit=self.rph
            )
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": f"{self.rph} requests per hour",
                    "retry_after": 3600 - (now - recent_hour[0]).seconds
                },
                headers={"Retry-After": "3600"}
            )
        
        self.requests[client_ip].append(now)
        
        self._save_periodically()
        
        limits_info = {
            "requests_this_minute": len(recent_minute) + 1,
            "requests_this_hour": len(recent_hour) + 1,
            "limit_per_minute": self.rpm,
            "limit_per_hour": self.rph,
            "remaining_minute": self.rpm - len(recent_minute) - 1,
            "remaining_hour": self.rph - len(recent_hour) - 1
        }
        
        return True, limits_info
    
    def reset_client(self, client_ip: str):
        """Reset rate limits for a specific client."""
        if client_ip in self.requests:
            del self.requests[client_ip]
            self._save()
            logger.info(f"Reset rate limits for {client_ip}")
    
    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        
        total_ips = len(self.requests)
        total_requests = sum(
            len([ts for ts in timestamps if ts > one_hour_ago])
            for timestamps in self.requests.values()
        )
        
        return {
            "total_tracked_ips": total_ips,
            "total_requests_last_hour": total_requests,
            "limits": {
                "per_minute": self.rpm,
                "per_hour": self.rph
            }
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to apply rate limiting to all requests."""
    
    BYPASS_PATHS = ["/health", "/docs", "/redoc", "/openapi.json"]
    
    def __init__(self, app, rpm: int = 60, rph: int = 1000):
        """Initialize middleware with rate limiter."""
        super().__init__(app)
        self.limiter = RateLimiter(
            requests_per_minute=rpm,
            requests_per_hour=rph
        )
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting to request."""
        if any(request.url.path.startswith(path) for path in self.BYPASS_PATHS):
            return await call_next(request)
        
        client_ip = request.client.host if request.client else "unknown"
        
        try:
            is_allowed, limits_info = self.limiter.check_rate_limit(
                client_ip,
                endpoint=request.url.path
            )
            
            response = await call_next(request)
            
            response.headers["X-RateLimit-Limit-Minute"] = str(limits_info["limit_per_minute"])
            response.headers["X-RateLimit-Limit-Hour"] = str(limits_info["limit_per_hour"])
            response.headers["X-RateLimit-Remaining-Minute"] = str(limits_info["remaining_minute"])
            response.headers["X-RateLimit-Remaining-Hour"] = str(limits_info["remaining_hour"])
            
            return response
            
        except HTTPException as e:
            raise e


rate_limiter = RateLimiter()

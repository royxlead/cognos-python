"""Request logging middleware."""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logger import get_logger
from app.core.metrics import metrics_collector
import time

logger = get_logger("requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all API requests and collect metrics."""
    
    async def dispatch(self, request: Request, call_next):
        """Log request and response with metrics collection."""
        # Start timer
        start_time = time.time()
        
        # Get request details
        method = request.method
        path = str(request.url.path)
        client = request.client.host if request.client else "unknown"
        
        # Call the endpoint
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        duration_ms = duration * 1000
        
        # Log the request
        logger.log_api_request(
            method=method,
            path=path,
            status_code=response.status_code,
            duration=duration,
            client=client
        )
        
        # Record metrics
        metrics_collector.record_api_request(
            method=method,
            path=path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=client
        )
        
        # Add custom headers
        response.headers["X-Process-Time"] = str(round(duration_ms, 2))
        
        return response

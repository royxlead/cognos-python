"""Global error handling middleware for COGNOS."""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.logger import get_logger
import traceback
from datetime import datetime

logger = get_logger("error_handler")


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.warning(
        f"HTTP Exception: {exc.status_code}",
        path=str(request.url.path),
        method=request.method,
        status_code=exc.status_code,
        detail=exc.detail
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
            "path": str(request.url.path),
            "timestamp": datetime.now().isoformat()
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    errors = exc.errors()
    
    logger.warning(
        "Validation Error",
        path=str(request.url.path),
        method=request.method,
        errors=errors
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "status_code": 422,
            "message": "Validation error",
            "details": errors,
            "path": str(request.url.path),
            "timestamp": datetime.now().isoformat()
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    # Log the full error with traceback
    logger.error(
        "Unhandled Exception",
        error=exc,
        path=str(request.url.path),
        method=request.method,
        client=request.client.host if request.client else "unknown"
    )
    
    # Don't expose internal error details in production
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "status_code": 500,
            "message": "An unexpected error occurred. Please try again later.",
            "path": str(request.url.path),
            "timestamp": datetime.now().isoformat(),
            # Include error type for debugging (remove in production)
            "error_type": type(exc).__name__
        }
    )


def setup_exception_handlers(app):
    """Setup all exception handlers for the FastAPI app."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("Exception handlers registered")

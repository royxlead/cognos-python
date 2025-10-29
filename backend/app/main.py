"""Main FastAPI application."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.memory_manager import memory_manager
from app.core.local_storage import local_storage
from app.core.logger import get_logger
from app.middleware import setup_exception_handlers, RequestLoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.api import chat, memory, models, websocket, conversations, metrics, cache, health

logger = get_logger("main")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting COGNOS backend...")
    memory_manager.load()
    logger.info(f"Loaded {len(memory_manager.memories)} memories")
    
    yield
    
    logger.info("Shutting down COGNOS backend...")
    memory_manager.save()
    logger.info("Saved memories to disk")


app = FastAPI(
    title="COGNOS API",
    description="""
# Cognitive AI Assistant with Memory & Reasoning

COGNOS is a production-grade AI assistant with:

* 🧠 **Advanced Memory System** - Long-term memory with semantic search
* 💬 **Multi-Model Support** - Works with GPT-4, Claude, Gemini, and local models
* 🔒 **Privacy-First** - Local file-based storage, no external databases
* ⚡ **High Performance** - Caching, rate limiting, and optimization
* 📊 **Comprehensive Metrics** - Track usage, costs, and performance
* 🔍 **Smart Search** - Vector-based similarity search across conversations
* 🎯 **Context-Aware** - Automatic conversation summarization

## Quick Start

1. Get an API key from your LLM provider
2. Set up your environment variables
3. Start chatting via `/api/chat` endpoint
4. View conversation history at `/api/conversations`

## Key Features

### Security
- Input sanitization (XSS, SQL injection protection)
- Rate limiting (60 req/min, 1000 req/hour)
- File-based rate tracking for privacy

### Monitoring
- Real-time health checks (`/api/health`)
- Performance metrics (`/api/metrics`)
- Error tracking and analysis

### Performance
- Response caching to reduce API costs
- Automatic conversation summarization
- Optimized context management
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "chat",
            "description": "Chat endpoints for conversing with the AI assistant"
        },
        {
            "name": "conversations",
            "description": "Manage conversation history and retrieve past conversations"
        },
        {
            "name": "memory",
            "description": "Long-term memory management and semantic search"
        },
        {
            "name": "models",
            "description": "Available AI models and their configurations"
        },
        {
            "name": "metrics",
            "description": "Performance metrics, usage statistics, and monitoring"
        },
        {
            "name": "cache",
            "description": "Cache management for performance optimization"
        },
        {
            "name": "health",
            "description": "Health checks and system status monitoring"
        },
        {
            "name": "websocket",
            "description": "WebSocket connections for real-time chat streaming"
        }
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware, rpm=60, rph=1000)

app.add_middleware(RequestLoggingMiddleware)

setup_exception_handlers(app)

app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
app.include_router(models.router, prefix="/api/models", tags=["models"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["conversations"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(cache.router, prefix="/api/cache", tags=["cache"])
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])


@app.get("/")
async def root():
    """Root endpoint with basic info."""
    return {
        "name": "COGNOS API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/health",
        "metrics": "/api/metrics/summary"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

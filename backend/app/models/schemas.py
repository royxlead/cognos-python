"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ChatRequest(BaseModel):
    """Request for chat endpoint."""
    message: str = Field(..., min_length=1, max_length=10000)
    model: Optional[str] = None
    enable_reasoning: bool = True
    session_id: Optional[str] = None
    user_id: Optional[int] = None


class ReasoningStep(BaseModel):
    """Reasoning step in chain of thought."""
    step_number: int
    thought: str
    action: str
    observation: str
    confidence: float = Field(ge=0.0, le=1.0)


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    answer: str
    reasoning_steps: List[ReasoningStep] = []
    memories_used: int = 0
    confidence: float = Field(ge=0.0, le=1.0)
    method: str  # 'direct' or 'chain_of_thought'
    session_id: str


class MemoryCreate(BaseModel):
    """Create new memory."""
    content: str
    memory_type: str = Field(..., pattern="^(user_info|conversation|knowledge|preference)$")
    importance: float = Field(default=1.0, ge=0.0, le=10.0)
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}


class MemoryResponse(BaseModel):
    """Memory object response."""
    content: str
    memory_type: str
    importance: float
    timestamp: datetime
    access_count: int
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


class MemorySearchRequest(BaseModel):
    """Search memories by query."""
    query: str
    k: int = Field(default=5, ge=1, le=50)
    memory_type: Optional[str] = None
    session_id: Optional[str] = None


class MemoryStats(BaseModel):
    """Memory statistics."""
    total_memories: int
    by_type: Dict[str, int]
    avg_age_days: float
    oldest_memory: Optional[str] = None
    newest_memory: Optional[str] = None


class ModelInfo(BaseModel):
    """Model information."""
    name: str
    available: bool
    current: bool


class ModelSwitchRequest(BaseModel):
    """Request to switch model."""
    model: str


class TaskInfo(BaseModel):
    """Task information."""
    id: str
    description: str
    dependencies: List[str]
    status: str
    result: Optional[str] = None
    error: Optional[str] = None


class TaskPlanResponse(BaseModel):
    """Task plan execution response."""
    tasks: List[TaskInfo]
    results: List[Dict[str, Any]]
    final_result: str
    status: str


class ErrorResponse(BaseModel):
    """Error response."""
    detail: str
    error_type: str = "general_error"


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    models_available: int
    memories_count: int
    timestamp: datetime

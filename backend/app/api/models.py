"""Models API endpoints."""
import logging
from fastapi import APIRouter, HTTPException
from typing import List
from app.models.schemas import ModelInfo, ModelSwitchRequest
from app.core.llm_manager import llm_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[ModelInfo])
async def list_models():
    """List all available models."""
    try:
        models = llm_manager.get_available_models()
        return [ModelInfo(**model) for model in models]
        
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/switch")
async def switch_model(request: ModelSwitchRequest):
    """Switch to a different model."""
    try:
        success = llm_manager.switch_model(request.model)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{request.model}' not available"
            )
        
        return {
            "status": "switched",
            "model": request.model
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_models_status():
    """Get detailed status of all models."""
    try:
        models = llm_manager.get_available_models()
        
        return {
            "current_model": llm_manager.current_model,
            "models": models,
            "total": len(models),
            "available": sum(1 for m in models if m['available'])
        }
        
    except Exception as e:
        logger.error(f"Error getting models status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current")
async def get_current_model():
    """Get currently active model."""
    try:
        return {
            "model": llm_manager.current_model,
            "available": llm_manager.get_service().is_available()
        }
        
    except Exception as e:
        logger.error(f"Error getting current model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

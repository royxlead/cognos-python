"""LLM Manager for multi-model support (Gemini, OpenAI, Ollama)."""
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import time
import requests
import google.generativeai as genai
from openai import AsyncOpenAI
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BaseLLMService(ABC):
    """Abstract base class for LLM services."""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text response from prompt."""
        pass
    
    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the service is available."""
        pass


class GeminiService(BaseLLMService):
    """Google Gemini API service."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        if api_key:
            genai.configure(api_key=api_key)
            # Use configurable Gemini model variant
            self.model_name = settings.GEMINI_MODEL or 'gemini-pro'
            self.model = genai.GenerativeModel(self.model_name)
            self.embedding_model = settings.GEMINI_EMBEDDING_MODEL or 'models/embedding-001'
        else:
            self.model = None
            self.model_name = None
            self.embedding_model = None
    
    def is_available(self) -> bool:
        """Check if Gemini API is configured and available."""
        return self.api_key is not None and self.model is not None
    
    async def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> str:
        """Generate text using Gemini API."""
        if not self.is_available():
            raise ValueError("Gemini API key not configured")
        
        try:
            # Allow per-call override of model variant if provided
            model_override = kwargs.get('model')
            model = genai.GenerativeModel(model_override) if model_override else self.model
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            response = await model.generate_content_async(
                prompt,
                generation_config=generation_config
            )
            
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Gemini embedding model."""
        if not self.is_available():
            raise ValueError("Gemini API key not configured")
        
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Gemini embedding error: {e}")
            raise


class OpenAIService(BaseLLMService):
    """OpenAI API service."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None
        self.model_name = "gpt-4o"
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL or "text-embedding-3-small"
    
    def is_available(self) -> bool:
        """Check if OpenAI API is configured."""
        return self.api_key is not None and self.client is not None
    
    async def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> str:
        """Generate text using OpenAI API."""
        if not self.is_available():
            raise ValueError("OpenAI API key not configured")
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI embedding model."""
        if not self.is_available():
            raise ValueError("OpenAI API key not configured")
        
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise


class OllamaService(BaseLLMService):
    """Local Ollama service."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.model_name = "llama2"
        # Prefer a dedicated embedding model
        self.embedding_model = getattr(settings, 'OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text')
    
    def is_available(self) -> bool:
        """Check if Ollama server is running."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False
    
    async def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000, **kwargs) -> str:
        """Generate text using Ollama API."""
        if not self.is_available():
            raise ValueError("Ollama server not available")
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Ollama."""
        if not self.is_available():
            raise ValueError("Ollama server not available")
        
        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.embedding_model,
                    "prompt": text
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()["embedding"]
        except Exception as e:
            logger.error(f"Ollama embedding error: {e}")
            raise


class LLMManager:
    """Manager for routing LLM requests to appropriate provider."""
    
    def __init__(self):
        self.services: Dict[str, BaseLLMService] = {
            "gemini": GeminiService(settings.GEMINI_API_KEY),
            "openai": OpenAIService(settings.OPENAI_API_KEY),
            "ollama": OllamaService(settings.OLLAMA_BASE_URL),
        }
        self.current_model = settings.DEFAULT_MODEL
        self._fallback_order = ["gemini", "openai", "ollama"]
    
    def get_service(self, model_name: Optional[str] = None) -> BaseLLMService:
        """Get LLM service by name or use current model."""
        model_name = model_name or self.current_model
        
        if model_name not in self.services:
            raise ValueError(f"Unknown model: {model_name}")
        
        service = self.services[model_name]
        
        if not service.is_available():
            logger.warning(f"Model {model_name} not available, trying fallback")
            return self._get_fallback_service()
        
        return service
    
    def _get_fallback_service(self) -> BaseLLMService:
        """Get first available fallback service."""
        for model_name in self._fallback_order:
            service = self.services.get(model_name)
            if service and service.is_available():
                logger.info(f"Using fallback model: {model_name}")
                return service
        
        raise RuntimeError("No LLM services available")
    
    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """Generate text using specified or current model."""
        service = self.get_service(model)
        return await service.generate(prompt, **kwargs)
    
    async def generate_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        """Generate embedding using specified or current model."""
        service = self.get_service(model)
        try:
            return await service.generate_embedding(text)
        except Exception as e:
            # Respect configuration: by default, do NOT fall back to other providers
            if not getattr(settings, "EMBEDDING_FALLBACK_ENABLED", False):
                raise
            logger.warning(f"Primary embedding provider failed ({type(service).__name__}): {e}. Trying fallbacks...")
            # Try other providers in fallback order excluding the original
            attempted = {service}
            for name in self._fallback_order:
                fallback = self.services.get(name)
                if not fallback or fallback in attempted:
                    continue
                if not fallback.is_available():
                    continue
                try:
                    logger.info(f"Attempting embedding with fallback provider: {name}")
                    return await fallback.generate_embedding(text)
                except Exception as fe:
                    logger.warning(f"Fallback provider '{name}' failed to embed: {fe}")
                    continue
            # If all fail, re-raise to let callers decide how to handle
            raise
    
    def switch_model(self, model_name: str) -> bool:
        """Switch to a different model."""
        if model_name not in self.services:
            return False
        
        service = self.services[model_name]
        if not service.is_available():
            return False
        
        self.current_model = model_name
        logger.info(f"Switched to model: {model_name}")
        return True
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models with status."""
        models = []
        for name, service in self.services.items():
            models.append({
                "name": name,
                "available": service.is_available(),
                "current": name == self.current_model
            })
        return models


# Global LLM manager instance
llm_manager = LLMManager()

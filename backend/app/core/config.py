"""Configuration module for COGNOS backend."""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"
    
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"

    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    DATABASE_URL: str = "postgresql://cognos:cognos_password@localhost:5432/cognos"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    DEFAULT_MODEL: str = "gemini"
    EMBEDDING_FALLBACK_ENABLED: bool = False
    VECTOR_DIM: int = 768
    MAX_MEMORIES: int = 1000
    MEMORY_DECAY_DAYS: int = 90
    
    ENABLE_COT: bool = True
    MAX_REASONING_STEPS: int = 5
    MIN_CONFIDENCE_THRESHOLD: float = 0.7
    
    MAX_CONTEXT_TOKENS: int = 4000
    SHORT_TERM_MEMORY_SIZE: int = 10
    
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    SECRET_KEY: str = "your_secret_key_here_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    DATA_DIR: str = "data"
    MEMORY_INDEX_PATH: str = "data/memory_index.faiss"
    MEMORY_METADATA_PATH: str = "data/memory_metadata.pkl"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
    def get_cors_origins(self) -> list:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    
    # Create data directory if it doesn't exist
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    
    return settings

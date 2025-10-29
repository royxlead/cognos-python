"""Local file-based caching system for performance optimization."""
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from app.core.logger import get_logger

logger = get_logger("cache")


class LocalCache:
    """Privacy-first local file-based cache."""
    
    def __init__(self, cache_dir: str = "data/cache", default_ttl: int = 3600):
        """
        Initialize local cache.
        
        Args:
            cache_dir: Directory to store cache files
            default_ttl: Default time-to-live in seconds
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
    
    def _get_cache_path(self, key: str) -> Path:
        """Get file path for cache key."""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        cache_file = self._get_cache_path(key)
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            expires_at = datetime.fromisoformat(data['expires_at'])
            if datetime.now() > expires_at:
                cache_file.unlink()
                logger.debug(f"Cache expired and deleted: {key}")
                return None
            
            logger.debug(f"Cache hit: {key}")
            return data['value']
            
        except Exception as e:
            logger.error(f"Error reading cache for {key}", error=e)
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None = use default)
        """
        if ttl is None:
            ttl = self.default_ttl
        
        cache_file = self._get_cache_path(key)
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        try:
            data = {
                'key': key,
                'value': value,
                'created_at': datetime.now().isoformat(),
                'expires_at': expires_at.isoformat(),
                'ttl': ttl
            }
            
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            
        except Exception as e:
            logger.error(f"Error setting cache for {key}", error=e)
    
    def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        cache_file = self._get_cache_path(key)
        
        if cache_file.exists():
            cache_file.unlink()
            logger.debug(f"Cache deleted: {key}")
            return True
        
        return False
    
    def clear(self):
        """Clear all cached values."""
        deleted_count = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                deleted_count += 1
            except Exception as e:
                logger.error(f"Error deleting cache file {cache_file}", error=e)
        
        logger.info(f"Cleared {deleted_count} cache files")
        return deleted_count
    
    def cleanup_expired(self):
        """Delete all expired cache files."""
        now = datetime.now()
        deleted_count = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                expires_at = datetime.fromisoformat(data['expires_at'])
                if now > expires_at:
                    cache_file.unlink()
                    deleted_count += 1
                    
            except Exception as e:
                logger.error(f"Error checking cache file {cache_file}", error=e)
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired cache files")
        
        return deleted_count
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        total_files = 0
        total_size = 0
        expired_count = 0
        now = datetime.now()
        
        for cache_file in self.cache_dir.glob("*.json"):
            total_files += 1
            total_size += cache_file.stat().st_size
            
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                expires_at = datetime.fromisoformat(data['expires_at'])
                if now > expires_at:
                    expired_count += 1
                    
            except Exception:
                pass
        
        return {
            "total_entries": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "expired_entries": expired_count,
            "cache_directory": str(self.cache_dir.absolute())
        }


class CachedLLMService:
    """Wrapper for LLM service with caching."""
    
    def __init__(self, llm_service, cache: LocalCache):
        """
        Initialize cached LLM service.
        
        Args:
            llm_service: Underlying LLM service
            cache: Cache instance
        """
        self.llm_service = llm_service
        self.cache = cache
    
    def _make_cache_key(self, prompt: str, **kwargs) -> str:
        """Create cache key from prompt and parameters."""
        # Include model and key parameters in cache key
        key_parts = [
            prompt,
            str(kwargs.get('max_tokens', '')),
            str(kwargs.get('temperature', '')),
            str(kwargs.get('model', ''))
        ]
        return hashlib.sha256('|'.join(key_parts).encode()).hexdigest()
    
    async def generate_cached(
        self,
        prompt: str,
        cache_ttl: int = 3600,
        force_refresh: bool = False,
        **kwargs
    ) -> str:
        """
        Generate response with caching.
        
        Args:
            prompt: Input prompt
            cache_ttl: Cache time-to-live
            force_refresh: Force new generation even if cached
            **kwargs: Additional LLM parameters
            
        Returns:
            Generated response
        """
        cache_key = self._make_cache_key(prompt, **kwargs)
        
        # Check cache
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.info("Using cached LLM response")
                return cached
        
        # Generate new response
        response = await self.llm_service.generate(prompt, **kwargs)
        
        # Cache the response
        self.cache.set(cache_key, response, ttl=cache_ttl)
        
        return response


cache = LocalCache()

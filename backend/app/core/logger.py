"""Structured logging system for COGNOS."""
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import traceback


class StructuredLogger:
    """Privacy-first structured logger with file rotation."""
    
    def __init__(self, name: str, log_dir: str = "data/logs"):
        """Initialize structured logger."""
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup file and console handlers."""
        # File handler (daily rotation)
        log_file = self.log_dir / f"{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def _log_structured(self, level: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Log structured data."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "logger": self.name,
            "level": level,
            "message": message
        }
        
        if data:
            log_entry["data"] = data
        
        log_method = getattr(self.logger, level.lower())
        log_method(json.dumps(log_entry, ensure_ascii=False))
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log_structured("INFO", message, kwargs if kwargs else None)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log_structured("WARNING", message, kwargs if kwargs else None)
    
    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log error message with optional exception."""
        data = kwargs.copy() if kwargs else {}
        
        if error:
            data["error"] = {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc()
            }
        
        self._log_structured("ERROR", message, data)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log_structured("DEBUG", message, kwargs if kwargs else None)
    
    def log_api_request(self, method: str, path: str, status_code: int, duration: float, **kwargs):
        """Log API request."""
        self.info(
            f"API Request: {method} {path}",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=round(duration * 1000, 2),
            **kwargs
        )
    
    def log_llm_call(self, model: str, tokens: int, duration: float, cost: float = 0.0):
        """Log LLM API call."""
        self.info(
            f"LLM Call: {model}",
            model=model,
            tokens=tokens,
            duration_s=round(duration, 2),
            cost_usd=round(cost, 4)
        )
    
    def log_memory_operation(self, operation: str, count: int = 1, **kwargs):
        """Log memory operation."""
        self.info(
            f"Memory: {operation}",
            operation=operation,
            count=count,
            **kwargs
        )
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Delete logs older than specified days."""
        cutoff_date = datetime.now().timestamp() - (days_to_keep * 86400)
        
        deleted_count = 0
        for log_file in self.log_dir.glob("*.log"):
            if log_file.stat().st_mtime < cutoff_date:
                log_file.unlink()
                deleted_count += 1
        
        if deleted_count > 0:
            self.info(f"Cleaned up {deleted_count} old log files")
        
        return deleted_count


# Global logger instances
def get_logger(name: str) -> StructuredLogger:
    """Get or create a structured logger."""
    return StructuredLogger(name)


# Common loggers
api_logger = get_logger("api")
core_logger = get_logger("core")
memory_logger = get_logger("memory")
llm_logger = get_logger("llm")

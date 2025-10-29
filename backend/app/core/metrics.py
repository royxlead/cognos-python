"""Metrics collection system for monitoring and analytics."""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict
from app.core.logger import get_logger

logger = get_logger("metrics")


class MetricsCollector:
    """Privacy-first metrics collection and analysis."""
    
    def __init__(self, storage_dir: str = "data/metrics"):
        """
        Initialize metrics collector.
        
        Args:
            storage_dir: Directory to store metrics data
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory metrics (reset periodically)
        self.api_requests: List[Dict] = []
        self.llm_calls: List[Dict] = []
        self.errors: List[Dict] = []
        self.memory_operations: List[Dict] = []
        
        # Load today's metrics
        self._load_today()
    
    def _get_metrics_file(self, date: Optional[datetime] = None) -> Path:
        """Get metrics file path for date."""
        if date is None:
            date = datetime.now()
        
        return self.storage_dir / f"metrics_{date.strftime('%Y%m%d')}.json"
    
    def _load_today(self):
        """Load today's metrics from file."""
        metrics_file = self._get_metrics_file()
        
        if metrics_file.exists():
            try:
                with open(metrics_file, 'r') as f:
                    data = json.load(f)
                    self.api_requests = data.get("api_requests", [])
                    self.llm_calls = data.get("llm_calls", [])
                    self.errors = data.get("errors", [])
                    self.memory_operations = data.get("memory_operations", [])
            except Exception as e:
                logger.error("Failed to load metrics", error=e)
    
    def _save(self):
        """Save current metrics to file."""
        metrics_file = self._get_metrics_file()
        
        try:
            data = {
                "api_requests": self.api_requests,
                "llm_calls": self.llm_calls,
                "errors": self.errors,
                "memory_operations": self.memory_operations,
                "last_updated": datetime.now().isoformat()
            }
            
            with open(metrics_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
        except Exception as e:
            logger.error("Failed to save metrics", error=e)
    
    def record_api_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        client_ip: Optional[str] = None
    ):
        """
        Record API request metrics.
        
        Args:
            method: HTTP method
            path: Request path
            status_code: Response status code
            duration_ms: Request duration in milliseconds
            client_ip: Client IP address
        """
        self.api_requests.append({
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "client_ip": client_ip
        })
        
        # Save periodically (every 10 requests)
        if len(self.api_requests) % 10 == 0:
            self._save()
    
    def record_llm_call(
        self,
        model: str,
        tokens: int,
        duration_s: float,
        cost_usd: float = 0.0,
        success: bool = True
    ):
        """
        Record LLM API call metrics.
        
        Args:
            model: LLM model name
            tokens: Number of tokens used
            duration_s: Call duration in seconds
            cost_usd: Estimated cost in USD
            success: Whether call succeeded
        """
        self.llm_calls.append({
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "tokens": tokens,
            "duration_s": round(duration_s, 2),
            "cost_usd": round(cost_usd, 4),
            "success": success
        })
        
        if len(self.llm_calls) % 5 == 0:
            self._save()
    
    def record_error(
        self,
        error_type: str,
        error_message: str,
        endpoint: Optional[str] = None,
        severity: str = "error"
    ):
        """
        Record error occurrence.
        
        Args:
            error_type: Type of error
            error_message: Error message
            endpoint: Endpoint where error occurred
            severity: Error severity (error, warning, critical)
        """
        self.errors.append({
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message[:200],  # Truncate long messages
            "endpoint": endpoint,
            "severity": severity
        })
        
        self._save()  # Always save errors immediately
    
    def record_memory_operation(
        self,
        operation: str,
        count: int = 1,
        duration_ms: Optional[float] = None
    ):
        """
        Record memory operation metrics.
        
        Args:
            operation: Operation type (add, retrieve, search, etc.)
            count: Number of items operated on
            duration_ms: Operation duration in milliseconds
        """
        self.memory_operations.append({
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "count": count,
            "duration_ms": round(duration_ms, 2) if duration_ms else None
        })
        
        if len(self.memory_operations) % 10 == 0:
            self._save()
    
    def get_api_stats(self, hours: int = 24) -> Dict:
        """
        Get API request statistics.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dictionary of API statistics
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        
        recent_requests = [
            r for r in self.api_requests
            if datetime.fromisoformat(r["timestamp"]) > cutoff
        ]
        
        if not recent_requests:
            return {
                "total_requests": 0,
                "requests_per_hour": 0,
                "avg_duration_ms": 0,
                "error_rate": 0,
                "by_status_code": {},
                "by_endpoint": {}
            }
        
        # Calculate statistics
        total = len(recent_requests)
        durations = [r["duration_ms"] for r in recent_requests]
        status_codes = defaultdict(int)
        endpoints = defaultdict(int)
        errors = 0
        
        for req in recent_requests:
            status_codes[req["status_code"]] += 1
            endpoints[req["path"]] += 1
            if req["status_code"] >= 400:
                errors += 1
        
        return {
            "total_requests": total,
            "requests_per_hour": round(total / hours, 2),
            "avg_duration_ms": round(sum(durations) / len(durations), 2),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "error_rate": round((errors / total) * 100, 2),
            "by_status_code": dict(status_codes),
            "by_endpoint": dict(sorted(
                endpoints.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10])  # Top 10 endpoints
        }
    
    def get_llm_stats(self, hours: int = 24) -> Dict:
        """
        Get LLM usage statistics.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dictionary of LLM statistics
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        
        recent_calls = [
            c for c in self.llm_calls
            if datetime.fromisoformat(c["timestamp"]) > cutoff
        ]
        
        if not recent_calls:
            return {
                "total_calls": 0,
                "total_tokens": 0,
                "total_cost_usd": 0,
                "avg_tokens_per_call": 0,
                "by_model": {}
            }
        
        total_tokens = sum(c["tokens"] for c in recent_calls)
        total_cost = sum(c["cost_usd"] for c in recent_calls)
        by_model = defaultdict(lambda: {"calls": 0, "tokens": 0, "cost": 0})
        
        for call in recent_calls:
            model = call["model"]
            by_model[model]["calls"] += 1
            by_model[model]["tokens"] += call["tokens"]
            by_model[model]["cost"] += call["cost_usd"]
        
        return {
            "total_calls": len(recent_calls),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "avg_tokens_per_call": round(total_tokens / len(recent_calls), 2),
            "avg_cost_per_call_usd": round(total_cost / len(recent_calls), 4),
            "by_model": {
                model: {
                    "calls": stats["calls"],
                    "tokens": stats["tokens"],
                    "cost_usd": round(stats["cost"], 4)
                }
                for model, stats in by_model.items()
            }
        }
    
    def get_error_stats(self, hours: int = 24) -> Dict:
        """
        Get error statistics.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dictionary of error statistics
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        
        recent_errors = [
            e for e in self.errors
            if datetime.fromisoformat(e["timestamp"]) > cutoff
        ]
        
        if not recent_errors:
            return {
                "total_errors": 0,
                "by_type": {},
                "by_severity": {},
                "by_endpoint": {}
            }
        
        by_type = defaultdict(int)
        by_severity = defaultdict(int)
        by_endpoint = defaultdict(int)
        
        for error in recent_errors:
            by_type[error["error_type"]] += 1
            by_severity[error["severity"]] += 1
            if error["endpoint"]:
                by_endpoint[error["endpoint"]] += 1
        
        return {
            "total_errors": len(recent_errors),
            "by_type": dict(by_type),
            "by_severity": dict(by_severity),
            "by_endpoint": dict(by_endpoint)
        }
    
    def get_memory_stats(self, hours: int = 24) -> Dict:
        """
        Get memory operation statistics.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dictionary of memory statistics
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        
        recent_ops = [
            op for op in self.memory_operations
            if datetime.fromisoformat(op["timestamp"]) > cutoff
        ]
        
        if not recent_ops:
            return {
                "total_operations": 0,
                "by_operation": {}
            }
        
        by_operation = defaultdict(lambda: {"count": 0, "items": 0})
        
        for op in recent_ops:
            operation = op["operation"]
            by_operation[operation]["count"] += 1
            by_operation[operation]["items"] += op["count"]
        
        return {
            "total_operations": len(recent_ops),
            "by_operation": dict(by_operation)
        }
    
    def get_summary(self, hours: int = 24) -> Dict:
        """
        Get comprehensive metrics summary.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dictionary of all metrics
        """
        return {
            "period_hours": hours,
            "generated_at": datetime.now().isoformat(),
            "api": self.get_api_stats(hours),
            "llm": self.get_llm_stats(hours),
            "errors": self.get_error_stats(hours),
            "memory": self.get_memory_stats(hours)
        }
    
    def cleanup_old_metrics(self, days_to_keep: int = 30):
        """
        Delete metrics files older than specified days.
        
        Args:
            days_to_keep: Number of days to keep
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        deleted_count = 0
        
        for metrics_file in self.storage_dir.glob("metrics_*.json"):
            try:
                # Extract date from filename
                date_str = metrics_file.stem.split('_')[1]
                file_date = datetime.strptime(date_str, '%Y%m%d')
                
                if file_date < cutoff_date:
                    metrics_file.unlink()
                    deleted_count += 1
            except Exception as e:
                logger.error(f"Error cleaning up metrics file {metrics_file}", error=e)
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old metrics files")
        
        return deleted_count


# Global metrics instance
metrics_collector = MetricsCollector()

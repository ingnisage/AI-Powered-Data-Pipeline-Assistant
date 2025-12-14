# backend/services/monitoring.py - Monitoring and Observability
"""
Monitoring and observability utilities for ai_workbench components.
Now consolidated in the backend/services folder.
"""

import time
import logging
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime

from .config import config
from ..utils import save_log
from ..models.logging import LogSource

logger = logging.getLogger(__name__)


@dataclass
class OperationMetrics:
    """Metrics for a single operation."""
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def complete(self, success: bool = True, error_message: Optional[str] = None):
        """Mark operation as complete."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.success = success
        self.error_message = error_message
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "operation_name": self.operation_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


class MetricsCollector:
    """Collects and reports metrics for ai_workbench operations."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.operations: Dict[str, OperationMetrics] = {}
        self.active_operations: Dict[str, OperationMetrics] = {}
        logger.info("MetricsCollector initialized")
    
    def start_operation(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Start tracking an operation.
        
        Args:
            operation_name: Name of the operation
            metadata: Additional metadata about the operation
            
        Returns:
            Operation ID
        """
        operation_id = f"{operation_name}_{int(time.time() * 1000000)}"
        
        metrics = OperationMetrics(
            operation_name=operation_name,
            start_time=time.time(),
            metadata=metadata or {}
        )
        
        self.active_operations[operation_id] = metrics
        logger.debug(f"Started operation {operation_name} with ID {operation_id}")
        
        return operation_id
    
    def end_operation(self, operation_id: str, success: bool = True, error_message: Optional[str] = None):
        """End tracking an operation.
        
        Args:
            operation_id: Operation ID returned by start_operation
            success: Whether the operation was successful
            error_message: Error message if operation failed
        """
        if operation_id in self.active_operations:
            metrics = self.active_operations.pop(operation_id)
            metrics.complete(success, error_message)
            self.operations[operation_id] = metrics
            
            # Log the operation
            level = logging.INFO if success else logging.ERROR
            message = f"Operation {metrics.operation_name} completed in {metrics.duration_ms:.2f}ms"
            if not success:
                message += f" with error: {error_message}"
            
            logger.log(level, message, extra={"metrics": metrics.to_dict()})
            
            return metrics
        
        logger.warning(f"Attempted to end unknown operation ID: {operation_id}")
        return None
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of collected metrics.
        
        Returns:
            Dictionary with metrics summary
        """
        if not self.operations:
            return {"message": "No operations recorded"}
        
        total_operations = len(self.operations)
        successful_operations = sum(1 for op in self.operations.values() if op.success)
        failed_operations = total_operations - successful_operations
        
        durations = [op.duration_ms for op in self.operations.values() if op.duration_ms is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        
        # Group by operation name
        operation_stats = {}
        for op in self.operations.values():
            if op.operation_name not in operation_stats:
                operation_stats[op.operation_name] = {
                    "count": 0,
                    "successful": 0,
                    "failed": 0,
                    "total_duration": 0,
                    "avg_duration": 0
                }
            
            stats = operation_stats[op.operation_name]
            stats["count"] += 1
            if op.success:
                stats["successful"] += 1
            else:
                stats["failed"] += 1
            if op.duration_ms:
                stats["total_duration"] += op.duration_ms
        
        # Calculate averages
        for stats in operation_stats.values():
            if stats["count"] > 0:
                stats["avg_duration"] = stats["total_duration"] / stats["count"]
        
        return {
            "total_operations": total_operations,
            "successful_operations": successful_operations,
            "failed_operations": failed_operations,
            "success_rate": successful_operations / total_operations if total_operations > 0 else 0,
            "average_duration_ms": avg_duration,
            "max_duration_ms": max_duration,
            "min_duration_ms": min_duration,
            "operation_stats": operation_stats
        }


# Global metrics collector instance
metrics_collector = MetricsCollector()


@contextmanager
def monitored_operation(operation_name: str, metadata: Optional[Dict[str, Any]] = None, supabase_client=None):
    """Context manager for monitoring operations.
    
    Args:
        operation_name: Name of the operation
        metadata: Additional metadata about the operation
        supabase_client: Supabase client for logging metrics
    """
    operation_id = metrics_collector.start_operation(operation_name, metadata)
    
    try:
        yield
        metrics_collector.end_operation(operation_id, success=True)
        
        # Log to Supabase if client provided
        if supabase_client:
            metrics = metrics_collector.operations.get(operation_id)
            if metrics:
                save_log(
                    level="INFO",
                    message=f"Operation {operation_name} completed successfully in {metrics.duration_ms:.2f}ms",
                    source=LogSource.MONITORING,
                    component=operation_name,
                    duration_ms=int(metrics.duration_ms) if metrics.duration_ms else None,
                    metadata=metrics.to_dict(),
                    supabase_client=supabase_client
                )
                
    except Exception as e:
        metrics_collector.end_operation(operation_id, success=False, error_message=str(e))
        
        # Log to Supabase if client provided
        if supabase_client:
            metrics = metrics_collector.operations.get(operation_id)
            if metrics:
                save_log(
                    level="ERROR",
                    message=f"Operation {operation_name} failed: {str(e)}",
                    source=LogSource.MONITORING,
                    component=operation_name,
                    duration_ms=int(metrics.duration_ms) if metrics.duration_ms else None,
                    metadata=metrics.to_dict(),
                    supabase_client=supabase_client
                )
        
        # Re-raise the exception
        raise


def monitor_function(func: Callable):
    """Decorator to monitor function execution.
    
    Args:
        func: Function to monitor
        
    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        with monitored_operation(f"{func.__module__}.{func.__name__}"):
            return func(*args, **kwargs)
    
    async def async_wrapper(*args, **kwargs):
        with monitored_operation(f"{func.__module__}.{func.__name__}"):
            return await func(*args, **kwargs)
    
    # Return appropriate wrapper based on whether function is async
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return wrapper


def log_performance_metrics(supabase_client=None):
    """Log current performance metrics.
    
    Args:
        supabase_client: Supabase client for persisting metrics
    """
    summary = metrics_collector.get_metrics_summary()
    
    logger.info("Performance Metrics Summary", extra={"metrics_summary": summary})
    
    if supabase_client:
        save_log(
            level="INFO",
            message="Performance metrics summary generated",
            source=LogSource.MONITORING,
            component="performance_summary",
            metadata=summary,
            supabase_client=supabase_client
        )


# Performance counters for specific metrics
class PerformanceCounters:
    """Simple performance counters for tracking specific metrics."""
    
    def __init__(self):
        self.counters: Dict[str, int] = {}
        self.timings: Dict[str, list] = {}
    
    def increment(self, counter_name: str, amount: int = 1):
        """Increment a counter.
        
        Args:
            counter_name: Name of the counter
            amount: Amount to increment by
        """
        self.counters[counter_name] = self.counters.get(counter_name, 0) + amount
        logger.debug(f"Counter {counter_name} incremented by {amount}, now {self.counters[counter_name]}")
    
    def record_timing(self, timing_name: str, duration_ms: float):
        """Record a timing.
        
        Args:
            timing_name: Name of the timing metric
            duration_ms: Duration in milliseconds
        """
        if timing_name not in self.timings:
            self.timings[timing_name] = []
        self.timings[timing_name].append(duration_ms)
        
        # Keep only recent timings to prevent memory issues
        if len(self.timings[timing_name]) > 1000:
            self.timings[timing_name] = self.timings[timing_name][-1000:]
        
        logger.debug(f"Timing {timing_name} recorded: {duration_ms}ms")
    
    def get_counter(self, counter_name: str) -> int:
        """Get current value of a counter.
        
        Args:
            counter_name: Name of the counter
            
        Returns:
            Current counter value
        """
        return self.counters.get(counter_name, 0)
    
    def get_average_timing(self, timing_name: str) -> Optional[float]:
        """Get average timing for a metric.
        
        Args:
            timing_name: Name of the timing metric
            
        Returns:
            Average timing in milliseconds, or None if no timings recorded
        """
        timings = self.timings.get(timing_name, [])
        if not timings:
            return None
        return sum(timings) / len(timings)
    
    def get_timing_stats(self, timing_name: str) -> Dict[str, Any]:
        """Get statistics for a timing metric.
        
        Args:
            timing_name: Name of the timing metric
            
        Returns:
            Dictionary with timing statistics
        """
        timings = self.timings.get(timing_name, [])
        if not timings:
            return {"count": 0}
        
        return {
            "count": len(timings),
            "average_ms": sum(timings) / len(timings),
            "min_ms": min(timings),
            "max_ms": max(timings),
            "total_ms": sum(timings)
        }


# Global performance counters instance
performance_counters = PerformanceCounters()


# Health check utilities
def health_check_component(component_name: str, check_function: Callable, supabase_client=None) -> Dict[str, Any]:
    """Perform a health check on a component.
    
    Args:
        component_name: Name of the component
        check_function: Function that performs the health check
        supabase_client: Supabase client for logging results
        
    Returns:
        Dictionary with health check results
    """
    start_time = time.time()
    
    try:
        result = check_function()
        duration_ms = (time.time() - start_time) * 1000
        
        health_status = {
            "component": component_name,
            "status": "healthy",
            "result": result,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Health check passed for {component_name}", extra=health_status)
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        
        health_status = {
            "component": component_name,
            "status": "unhealthy",
            "error": str(e),
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.error(f"Health check failed for {component_name}: {e}", extra=health_status)
    
    # Log to Supabase if client provided
    if supabase_client:
        level = "INFO" if health_status["status"] == "healthy" else "ERROR"
        save_log(
            level=level,
            message=f"Health check for {component_name}: {health_status['status']}",
            source=LogSource.MONITORING,
            component="health_check",
            metadata=health_status,
            supabase_client=supabase_client
        )
    
    return health_status


def health_check_all_components(components: Dict[str, Callable], supabase_client=None) -> Dict[str, Any]:
    """Perform health checks on all components.
    
    Args:
        components: Dictionary mapping component names to check functions
        supabase_client: Supabase client for logging results
        
    Returns:
        Dictionary with overall health status and individual component statuses
    """
    results = {}
    all_healthy = True
    
    for component_name, check_function in components.items():
        try:
            result = health_check_component(component_name, check_function, supabase_client)
            results[component_name] = result
            if result["status"] != "healthy":
                all_healthy = False
        except Exception as e:
            results[component_name] = {
                "component": component_name,
                "status": "error",
                "error": f"Failed to run health check: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
            all_healthy = False
            logger.error(f"Error running health check for {component_name}: {e}")
    
    overall_status = {
        "status": "healthy" if all_healthy else "unhealthy",
        "components": results,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Overall health check status: {overall_status['status']}")
    
    return overall_status
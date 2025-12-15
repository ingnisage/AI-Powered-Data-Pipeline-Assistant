# backend/services/monitoring.py - Monitoring and Observability
"""
Monitoring and observability utilities for ai_workbench components.
Now consolidated in the backend/services folder.
"""

import logging
import time
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from contextlib import contextmanager

# Import performance monitoring utilities
from backend.core.performance_monitoring import (
    monitored_operation as base_monitored_operation,
    monitor_function as base_monitor_function,
    metrics_collector,
    performance_counters
)

from .config import config
from ..utils import save_log
from ..models.logging import LogSource

logger = logging.getLogger(__name__)


@contextmanager
def monitored_operation(operation_name: str, metadata: Optional[Dict[str, Any]] = None, supabase_client=None):
    """Context manager for monitoring operations with Supabase logging.
    
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
    """Decorator to monitor function execution with enhanced logging.
    
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
    """Log current performance metrics to Supabase.
    
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
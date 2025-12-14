# backend/services/__init__.py
"""
AI Workbench v2 package - Improved integration with backend services.
Now consolidated in the backend/services folder.
"""

import logging
logger = logging.getLogger(__name__)

__version__ = "2.0.0"
__author__ = "AI Workbench Team"


from .chat_processor import ChatProcessor
from .pubnub_job_processor import JobProcessor, PubNubJobListener, create_pubnub_job_processor
from ..utils import save_log, log_and_publish, save_chat_message
from .config import config
from .exceptions import *
from .retry import *
from .monitoring import *
from .resource_manager import *

__all__ = [
    "ChatProcessor",
    "JobProcessor",
    "PubNubJobListener",
    "create_pubnub_job_processor",
    "config",
    "AiWorkbenchError",
    "ConfigurationError",
    "ServiceInitializationError",
    "ProcessingError",
    "NetworkError",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError",
    "handle_exception",
    "safe_execute",
    "RetryConfig",
    "retry_with_backoff",
    "retry_sync_operation",
    "retry_async_operation",
    "DEFAULT_RETRY_CONFIG",
    "NETWORK_RETRY_CONFIG",
    "API_RETRY_CONFIG",
    "metrics_collector",
    "monitored_operation",
    "monitor_function",
    "log_performance_metrics",
    "performance_counters",
    "health_check_component",
    "health_check_all_components",
    "resource_manager",
    "managed_resource",
    "ResourcePool",
    "health_check_resource",
    "health_check_all_resources",
]


def initialize_ai_workbench_components(service_container):
    """Initialize AI Workbench components with backend service container.
    
    Args:
        service_container: Backend ServiceContainer instance
        
    Returns:
        Dictionary of initialized components
    """
    # Get required services from the container
    openai_client = service_container.get_openai_client()
    supabase_client = service_container.get_supabase_client()
    search_service = service_container.get_search_service()
    vector_service = service_container.get_vector_service()
    
    # Initialize components with proper dependency injection
    chat_processor = ChatProcessor(
        openai_client=openai_client,
        supabase_client=supabase_client,
        search_service=search_service,
        vector_service=vector_service
    )
    
    job_processor = JobProcessor(
        openai_client=openai_client,
        supabase_client=supabase_client
    )
    
    # Register top-level components with resource manager
    from .resource_manager import resource_manager
    resource_manager.register_resource("ai_workbench_chat_processor", chat_processor, "component")
    resource_manager.register_resource("ai_workbench_job_processor", job_processor, "component")
    
    return {
        "chat_processor": chat_processor,
        "job_processor": job_processor,
        "openai_client": openai_client,
        "supabase_client": supabase_client,
        "search_service": search_service,
        "vector_service": vector_service
    }

def cleanup_ai_workbench_components():
    """Clean up AI Workbench components and release all resources.
    
    This function should be called during application shutdown to properly
    clean up all managed resources.
    """
    from .resource_manager import resource_manager
    resource_manager.release_all_resources()
    logger.info("AI Workbench components cleaned up and resources released")
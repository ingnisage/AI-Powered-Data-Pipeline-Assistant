import os
import logging
from typing import Optional, Dict, Any
from functools import lru_cache
from contextlib import asynccontextmanager
import asyncio
from fastapi import Depends, FastAPI
from openai import OpenAI
from supabase import create_client, Client
import httpx
from httpx import Timeout
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Import Render configuration
try:
    from backend.core.render_config import get_render_optimized_config, is_render_environment
    RENDER_CONFIG = get_render_optimized_config() if is_render_environment() else {}
    IS_RENDER = is_render_environment()
except ImportError:
    RENDER_CONFIG = {}
    IS_RENDER = False

# Import SearchService and VectorStoreService
try:
    from backend.services.search_service import SearchService
    SEARCH_SERVICE_AVAILABLE = True
except ImportError:
    SEARCH_SERVICE_AVAILABLE = False
    logger.warning("SearchService not available")

try:
    from backend.services.vector_service import VectorStoreService
    VECTOR_SERVICE_AVAILABLE = True
except ImportError:
    VECTOR_SERVICE_AVAILABLE = False
    logger.warning("VectorStoreService not available")

logger = logging.getLogger(__name__)

# Retry decorator for Supabase operations
def retry_supabase_operation(max_retries: int = 3):
    """Decorator to add retry mechanism to Supabase operations."""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            # Handle async functions
            @retry(
                stop=stop_after_attempt(max_retries),
                wait=wait_exponential(multiplier=1, min=4, max=10),
                retry=retry_if_exception_type((
                    httpx.TimeoutException, 
                    httpx.NetworkError,
                    httpx.RemoteProtocolError,
                    ConnectionError
                )),
                reraise=True
            )
            async def async_wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            return async_wrapper
        else:
            # Handle sync functions
            @retry(
                stop=stop_after_attempt(max_retries),
                wait=wait_exponential(multiplier=1, min=4, max=10),
                retry=retry_if_exception_type((
                    httpx.TimeoutException, 
                    httpx.NetworkError,
                    httpx.RemoteProtocolError,
                    ConnectionError
                )),
                reraise=True
            )
            def sync_wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return sync_wrapper
    return decorator


class ServiceContainer:
    """Centralized service container for dependency management."""
    
    def __init__(self):
        """Initialize service container and all dependencies."""
        logger.info("Initializing ServiceContainer...")
        self._supabase_client: Optional[Client] = None
        self._openai_client: Optional[OpenAI] = None
        self._pubnub_client: Optional[PubNub] = None
        self._search_service: Optional[SearchService] = None
        self._vector_service: Optional[VectorStoreService] = None
        self._health_status: Dict[str, Dict[str, Any]] = {
            "supabase": {"status": "unknown", "error": None},
            "openai": {"status": "unknown", "error": None},
            "pubnub": {"status": "unknown", "error": None},
            "search": {"status": "unknown", "error": None},
            "vector": {"status": "unknown", "error": None}
        }
        
        # Initialize all services
        self._initialize_services()
        
        logger.info("ServiceContainer initialization complete")
    
    def _initialize_services(self):
        """Initialize all required services."""
        self._initialize_openai()
        self._initialize_supabase()
        self._initialize_pubnub()
        self._initialize_search_service()
        self._initialize_vector_service()
    
    def _initialize_openai(self):
        """Initialize OpenAI client."""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self._openai_client = OpenAI(api_key=api_key)
                self._health_status["openai"] = {"status": "healthy", "error": None}
                logger.info("OpenAI client initialized successfully")
            else:
                self._health_status["openai"] = {"status": "disabled", "error": "OPENAI_API_KEY not provided"}
                logger.warning("OpenAI client not initialized: API key not provided")
        except Exception as e:
            self._health_status["openai"] = {"status": "error", "error": str(e)}
            logger.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)
    
    def _initialize_supabase(self):
        """Initialize Supabase with custom HTTP client for better timeout control."""
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            # Use SUPABASE_SERVICE_ROLE_KEY as primary, SUPABASE_KEY as fallback
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
            
            logger.info(f"Supabase config - URL: {supabase_url[:30] if supabase_url else 'None'}...")
            logger.info(f"Supabase key type: {'SERVICE_ROLE_KEY' if os.getenv('SUPABASE_SERVICE_ROLE_KEY') else 'SUPABASE_KEY (fallback)'}")
            logger.info(f"Supabase key present: {supabase_key is not None}")
            
            if supabase_url and supabase_key:
                logger.info("Initializing Supabase client...")
                
                # Create Supabase client (without http_client parameter)
                self._supabase_client = create_client(
                    supabase_url, 
                    supabase_key
                )
                
                self._health_status["supabase"] = {"status": "healthy", "error": None}
                logger.info("Supabase client initialized successfully")
                
                # Test the connection (simplified test without async)
                try:
                    logger.info("Testing Supabase connection...")
                    response = self._supabase_client.table("tasks").select("id").limit(1).execute()
                    logger.info(f"Supabase connection test successful. Sample response: {response.data if response else 'None'}")
                except Exception as test_error:
                    error_msg = f"Supabase connection test failed: {test_error}"
                    logger.error(error_msg)
                    self._health_status["supabase"] = {"status": "error", "error": error_msg}
            else:
                missing = []
                if not supabase_url:
                    missing.append("SUPABASE_URL")
                if not supabase_key:
                    missing.append("SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY")
                error_msg = f"Credentials not provided: {', '.join(missing)}"
                self._health_status["supabase"] = {"status": "disabled", "error": error_msg}
                logger.warning(f"Supabase client not initialized: {error_msg}")
        except Exception as e:
            error_msg = f"Failed to initialize Supabase client: {e}"
            self._health_status["supabase"] = {"status": "error", "error": error_msg}
            logger.error(f"Failed to initialize Supabase client: {e}", exc_info=True)
    
    def _initialize_pubnub(self):
        """Initialize PubNub client."""
        try:
            publish_key = os.getenv("PUBNUB_PUBLISH_KEY")
            subscribe_key = os.getenv("PUBNUB_SUBSCRIBE_KEY")
            
            if publish_key and subscribe_key:
                pnconfig = PNConfiguration()
                pnconfig.publish_key = publish_key
                pnconfig.subscribe_key = subscribe_key
                pnconfig.uuid = "ai-workbench-backend"
                pnconfig.ssl = True
                
                self._pubnub_client = PubNub(pnconfig)
                self._health_status["pubnub"] = {"status": "healthy", "error": None}
                logger.info("PubNub client initialized successfully")
            else:
                missing = []
                if not publish_key:
                    missing.append("PUBNUB_PUBLISH_KEY")
                if not subscribe_key:
                    missing.append("PUBNUB_SUBSCRIBE_KEY")
                error_msg = f"Credentials not provided: {', '.join(missing)}"
                self._health_status["pubnub"] = {"status": "disabled", "error": error_msg}
                logger.warning(f"PubNub client not initialized: {error_msg}")
        except Exception as e:
            self._health_status["pubnub"] = {"status": "error", "error": str(e)}
            logger.error(f"Failed to initialize PubNub client: {e}", exc_info=True)
    
    def _initialize_search_service(self):
        """Initialize SearchService."""
        try:
            if SEARCH_SERVICE_AVAILABLE:
                # Get clients for SearchService
                openai_client = self._openai_client
                supabase_client = self._supabase_client
                
                self._search_service = SearchService(
                    openai_client=openai_client,
                    supabase_client=supabase_client
                )
                self._health_status["search"] = {"status": "healthy", "error": None}
                logger.info("SearchService initialized successfully")
            else:
                self._health_status["search"] = {"status": "disabled", "error": "SearchService not available"}
                logger.warning("SearchService not available for initialization")
        except Exception as e:
            self._health_status["search"] = {"status": "error", "error": str(e)}
            logger.error(f"Failed to initialize SearchService: {e}", exc_info=True)
    
    def _initialize_vector_service(self):
        """Initialize VectorStoreService."""
        try:
            if VECTOR_SERVICE_AVAILABLE and self._openai_client and self._supabase_client:
                self._vector_service = VectorStoreService(
                    openai_client=self._openai_client,
                    supabase_client=self._supabase_client
                )
                self._health_status["vector"] = {"status": "healthy", "error": None}
                logger.info("VectorStoreService initialized successfully")
            elif VECTOR_SERVICE_AVAILABLE:
                self._health_status["vector"] = {"status": "disabled", "error": "VectorStoreService requires OpenAI and Supabase clients"}
                logger.warning("VectorStoreService not initialized: missing OpenAI or Supabase client")
            else:
                self._health_status["vector"] = {"status": "disabled", "error": "VectorStoreService not available"}
                logger.warning("VectorStoreService not available for initialization")
        except Exception as e:
            self._health_status["vector"] = {"status": "error", "error": str(e)}
            logger.error(f"Failed to initialize VectorStoreService: {e}", exc_info=True)
    
    def get_supabase_client(self) -> Optional[Client]:
        """Get Supabase client instance."""
        return self._supabase_client
    
    def get_openai_client(self) -> Optional[OpenAI]:
        """Get OpenAI client instance."""
        return self._openai_client
    
    def get_pubnub_client(self) -> Optional[PubNub]:
        """Get PubNub client instance."""
        return self._pubnub_client
    
    def get_search_service(self) -> Optional[SearchService]:
        """Get SearchService instance."""
        return self._search_service
    
    def get_vector_service(self) -> Optional[VectorStoreService]:
        """Get VectorStoreService instance."""
        return self._vector_service
    
    def get_health_status(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all services."""
        return self._health_status
    
    def cleanup(self):
        """Cleanup all resources."""
        logger.info("Cleaning up ServiceContainer resources...")
        
        # Cleanup Supabase (if needed)
        if self._supabase_client:
            try:
                # Close the HTTP client if it exists
                if hasattr(self._supabase_client, 'http_client') and self._supabase_client.http_client:
                    self._supabase_client.http_client.close()
                logger.info("Supabase client cleanup complete")
            except Exception as e:
                logger.error(f"Error cleaning up Supabase client: {e}", exc_info=True)
        
        # Cleanup PubNub
        if self._pubnub_client:
            try:
                self._pubnub_client.stop()
                logger.info("PubNub client cleanup complete")
            except Exception as e:
                logger.error(f"Error cleaning up PubNub client: {e}", exc_info=True)
        
        logger.info("ServiceContainer cleanup complete")


@lru_cache()
def get_container() -> ServiceContainer:
    """Get singleton service container instance."""
    return ServiceContainer()


def get_supabase_client():
    """Dependency for Supabase client."""
    container = get_container()
    return container.get_supabase_client()


def get_openai_client():
    """Dependency for OpenAI client."""
    container = get_container()
    return container.get_openai_client()


def get_pubnub_client():
    """Dependency for PubNub client."""
    container = get_container()
    return container.get_pubnub_client()


def get_search_service():
    """Dependency for SearchService."""
    container = get_container()
    return container.get_search_service()


def get_vector_service():
    """Dependency for VectorStoreService."""
    container = get_container()
    return container.get_vector_service()


# Add the missing lifespan function
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    logger.info("Starting application lifecycle...")
    
    # Startup: Initialize services
    container = get_container()
    
    # Register cleanup on shutdown
    try:
        yield
    finally:
        # Shutdown: Cleanup resources
        logger.info("Shutting down application...")
        container.cleanup()
        logger.info("Application shutdown complete")


# Add the missing get_service_health function
def get_service_health():
    """Get the health status of all services."""
    container = get_container()
    health_status = container.get_health_status()
    
    # Overall system health - healthy if all components are healthy or disabled
    overall_healthy = all(status["status"] in ["healthy", "disabled"] for status in health_status.values())
    
    return {
        "overall": overall_healthy,
        "services": health_status
    }
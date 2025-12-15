# core/dependencies.py - Dependency Injection and Service Management
"""
Centralized service container with dependency injection pattern.
Addresses global state issues, initialization race conditions, and provides proper lifecycle management.
"""

import os
import logging
from typing import Optional, Dict, Any
from functools import lru_cache
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from openai import OpenAI
from supabase import create_client, Client
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub

logger = logging.getLogger(__name__)


class ServiceContainer:
    """Singleton container for all application services with lifecycle management."""
    
    _instance: Optional['ServiceContainer'] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize service container (only once)."""
        if not self._initialized:
            self._openai_client: Optional[OpenAI] = None
            self._supabase_client: Optional[Client] = None
            self._pubnub_client: Optional[PubNub] = None
            self._search_service = None
            self._vector_service = None
            
            # Health check status
            self._health_status: Dict[str, Any] = {
                "openai": {"status": "not_initialized", "error": None},
                "supabase": {"status": "not_initialized", "error": None},
                "pubnub": {"status": "not_initialized", "error": None},
            }
            
            ServiceContainer._initialized = True
            logger.info("ServiceContainer created (singleton)")
    
    def initialize_services(self) -> None:
        """Initialize all services lazily with proper error handling.
        
        This should be called during application startup, not at import time.
        """
        logger.info("Initializing services...")
        
        # Initialize OpenAI
        try:
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                self._openai_client = OpenAI(api_key=openai_key)
                self._health_status["openai"] = {"status": "healthy", "error": None}
                logger.info("OpenAI client initialized successfully")
            else:
                self._health_status["openai"] = {"status": "disabled", "error": "API key not provided"}
                logger.warning("OpenAI client not initialized: API key missing")
        except Exception as e:
            self._health_status["openai"] = {"status": "error", "error": str(e)}
            logger.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)
        
        # Initialize Supabase
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            # Use SUPABASE_KEY as fallback if SERVICE_ROLE_KEY is not available
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
            
            if supabase_url and supabase_key:
                self._supabase_client = create_client(supabase_url, supabase_key)
                self._health_status["supabase"] = {"status": "healthy", "error": None}
                logger.info("Supabase client initialized successfully")
            else:
                self._health_status["supabase"] = {"status": "disabled", "error": "Credentials not provided"}
                logger.warning("Supabase client not initialized: credentials missing")
        except Exception as e:
            self._health_status["supabase"] = {"status": "error", "error": str(e)}
            logger.error(f"Failed to initialize Supabase client: {e}", exc_info=True)
        
        # Initialize PubNub
        try:
            publish_key = os.getenv("PUBNUB_PUBLISH_KEY", "demo")
            subscribe_key = os.getenv("PUBNUB_SUBSCRIBE_KEY", "demo")
            
            pnconfig = PNConfiguration()
            pnconfig.publish_key = publish_key
            pnconfig.subscribe_key = subscribe_key
            pnconfig.uuid = "ai-workbench-server"
            pnconfig.ssl = True
            
            self._pubnub_client = PubNub(pnconfig)
            self._health_status["pubnub"] = {"status": "healthy", "error": None}
            logger.info("PubNub client initialized successfully")
        except Exception as e:
            self._health_status["pubnub"] = {"status": "error", "error": str(e)}
            logger.error(f"Failed to initialize PubNub client: {e}", exc_info=True)
        
        logger.info("Service initialization complete")
    
    def cleanup_services(self) -> None:
        """Cleanup all services on application shutdown."""
        logger.info("Cleaning up services...")
        
        # Cleanup PubNub
        if self._pubnub_client:
            try:
                self._pubnub_client.stop()
                logger.info("PubNub client stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping PubNub client: {e}", exc_info=True)
        
        # Cleanup Supabase (if needed)
        if self._supabase_client:
            try:
                # Supabase client doesn't require explicit cleanup in most cases
                logger.info("Supabase client cleanup complete")
            except Exception as e:
                logger.error(f"Error cleaning up Supabase client: {e}", exc_info=True)
        
        # Reset health status
        for service in self._health_status:
            self._health_status[service] = {"status": "shutdown", "error": None}
        
        logger.info("Service cleanup complete")
    
    def get_openai_client(self) -> Optional[OpenAI]:
        """Get OpenAI client instance.
        
        Returns:
            OpenAI client or None if not initialized
            
        Raises:
            RuntimeError: If service is in error state
        """
        if self._health_status["openai"]["status"] == "error":
            raise RuntimeError(f"OpenAI service error: {self._health_status['openai']['error']}")
        return self._openai_client
    
    def get_supabase_client(self) -> Optional[Client]:
        """Get Supabase client instance.
        
        Returns:
            Supabase client or None if not initialized
            
        Raises:
            RuntimeError: If service is in error state
        """
        if self._health_status["supabase"]["status"] == "error":
            raise RuntimeError(f"Supabase service error: {self._health_status['supabase']['error']}")
        return self._supabase_client
    
    def get_pubnub_client(self) -> Optional[PubNub]:
        """Get PubNub client instance.
        
        Returns:
            PubNub client or None if not initialized
            
        Raises:
            RuntimeError: If service is in error state
        """
        if self._health_status["pubnub"]["status"] == "error":
            raise RuntimeError(f"PubNub service error: {self._health_status['pubnub']['error']}")
        return self._pubnub_client
    
    def get_search_service(self):
        """Get search service instance (lazy initialization)."""
        if self._search_service is None:
            try:
                # Import here to avoid circular dependencies
                from backend.services.search_engine import SearchService
                # Get the required clients
                openai_client = self.get_openai_client()
                supabase_client = self.get_supabase_client()
                self._search_service = SearchService(openai_client, supabase_client)
                logger.info("Search service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize search service: {e}", exc_info=True)
                raise
        return self._search_service
    
    def get_vector_service(self):
        """Get vector service instance (lazy initialization)."""
        if self._vector_service is None:
            try:
                # Import here to avoid circular dependencies
                # Placeholder for actual vector service implementation
                logger.info("Vector service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize vector service: {e}", exc_info=True)
                raise
        return self._vector_service
    
    def health_check(self) -> Dict[str, Any]:
        """Get health status of all services.
        
        Returns:
            Dictionary with health status of each service
        """
        return {
            "services": self._health_status.copy(),
            "overall": all(
                status["status"] in ("healthy", "disabled")
                for status in self._health_status.values()
            )
        }


# Global container instance
_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """Get the global ServiceContainer instance.
    
    Returns:
        ServiceContainer singleton instance
    """
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container


# FastAPI lifespan context manager for proper startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan with proper service initialization and cleanup.
    
    Args:
        app: FastAPI application instance
        
    Yields:
        Control to the application
    """
    # Startup
    logger.info("Application starting up...")
    container = get_container()
    container.initialize_services()
    
    # Log health status
    health = container.health_check()
    logger.info(f"Service health check: {health}")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Application shutting down...")
    container.cleanup_services()
    logger.info("Application shutdown complete")


# FastAPI dependency functions
@lru_cache()
def get_openai_client() -> Optional[OpenAI]:
    """FastAPI dependency for OpenAI client.
    
    Returns:
        OpenAI client instance
    """
    return get_container().get_openai_client()


@lru_cache()
def get_supabase_client() -> Optional[Client]:
    """FastAPI dependency for Supabase client.
    
    Returns:
        Supabase client instance
    """
    return get_container().get_supabase_client()


@lru_cache()
def get_pubnub_client() -> Optional[PubNub]:
    """FastAPI dependency for PubNub client.
    
    Returns:
        PubNub client instance
    """
    return get_container().get_pubnub_client()


def get_search_service():
    """FastAPI dependency for search service.
    
    Returns:
        Search service instance
    """
    return get_container().get_search_service()


def get_vector_service():
    """FastAPI dependency for vector service.
    
    Returns:
        Vector service instance
    """
    return get_container().get_vector_service()


# Health check endpoint helper
def get_service_health() -> Dict[str, Any]:
    """Get current health status of all services.
    
    Returns:
        Dictionary with health information
    """
    return get_container().health_check()

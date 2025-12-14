# backend/services/resource_manager.py - Resource Lifecycle Management
"""
Resource lifecycle management for ai_workbench components.
"""

import asyncio
import logging
import weakref
from typing import Dict, Any, Optional, Callable, Set
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime

from .exceptions import ServiceInitializationError

logger = logging.getLogger(__name__)


@dataclass
class ResourceInfo:
    """Information about a managed resource."""
    name: str
    resource: Any
    resource_type: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResourceManager:
    """Manages lifecycle of resources used by ai_workbench components."""
    
    def __init__(self):
        """Initialize resource manager."""
        self.resources: Dict[str, ResourceInfo] = {}
        self.resource_finalizers: Dict[str, Callable] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}
        logger.info("ResourceManager initialized")
    
    def register_resource(
        self, 
        name: str, 
        resource: Any, 
        resource_type: str,
        finalizer: Optional[Callable] = None,
        dependencies: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register a resource for lifecycle management.
        
        Args:
            name: Unique name for the resource
            resource: The resource to manage
            resource_type: Type of resource (e.g., 'client', 'connection', 'cache')
            finalizer: Optional cleanup function to call when resource is released
            dependencies: Set of resource names this resource depends on
            metadata: Optional metadata about the resource
            
        Returns:
            Resource name (may be modified for uniqueness)
        """
        # Ensure unique name
        original_name = name
        counter = 1
        while name in self.resources:
            name = f"{original_name}_{counter}"
            counter += 1
        
        # Create resource info
        resource_info = ResourceInfo(
            name=name,
            resource=resource,
            resource_type=resource_type,
            metadata=metadata or {}
        )
        
        # Register resource
        self.resources[name] = resource_info
        
        # Register finalizer if provided
        if finalizer:
            self.resource_finalizers[name] = finalizer
        
        # Register dependencies
        if dependencies:
            self.dependency_graph[name] = set(dependencies)
        
        logger.debug(f"Registered resource: {name} (type: {resource_type})")
        return name
    
    def get_resource(self, name: str) -> Optional[Any]:
        """Get a managed resource by name.
        
        Args:
            name: Name of the resource
            
        Returns:
            The resource, or None if not found
        """
        if name in self.resources:
            resource_info = self.resources[name]
            resource_info.last_accessed = datetime.utcnow()
            resource_info.access_count += 1
            return resource_info.resource
        return None
    
    def get_resource_info(self, name: str) -> Optional[ResourceInfo]:
        """Get information about a managed resource.
        
        Args:
            name: Name of the resource
            
        Returns:
            ResourceInfo, or None if not found
        """
        return self.resources.get(name)
    
    def list_resources(self, resource_type: Optional[str] = None) -> Dict[str, ResourceInfo]:
        """List all managed resources, optionally filtered by type.
        
        Args:
            resource_type: Optional resource type to filter by
            
        Returns:
            Dictionary of resource names to ResourceInfo
        """
        if resource_type:
            return {
                name: info for name, info in self.resources.items()
                if info.resource_type == resource_type
            }
        return self.resources.copy()
    
    def update_resource_metadata(self, name: str, metadata: Dict[str, Any]):
        """Update metadata for a resource.
        
        Args:
            name: Name of the resource
            metadata: Metadata to update
        """
        if name in self.resources:
            self.resources[name].metadata.update(metadata)
            logger.debug(f"Updated metadata for resource: {name}")
    
    def release_resource(self, name: str, force: bool = False) -> bool:
        """Release a managed resource.
        
        Args:
            name: Name of the resource to release
            force: Whether to force release even if there are dependencies
            
        Returns:
            True if resource was released, False otherwise
        """
        if name not in self.resources:
            logger.warning(f"Attempted to release non-existent resource: {name}")
            return False
        
        # Check dependencies
        if not force:
            # Check if any other resources depend on this one
            for resource_name, dependencies in self.dependency_graph.items():
                if name in dependencies and resource_name in self.resources:
                    logger.warning(f"Cannot release resource {name} - still referenced by {resource_name}")
                    return False
        
        # Call finalizer if registered
        if name in self.resource_finalizers:
            try:
                finalizer = self.resource_finalizers[name]
                finalizer()
                logger.debug(f"Executed finalizer for resource: {name}")
            except Exception as e:
                logger.error(f"Error executing finalizer for resource {name}: {e}")
        
        # Remove from dependency graph
        if name in self.dependency_graph:
            del self.dependency_graph[name]
        
        # Remove dependencies on this resource
        for dependencies in self.dependency_graph.values():
            dependencies.discard(name)
        
        # Remove from finalizers
        if name in self.resource_finalizers:
            del self.resource_finalizers[name]
        
        # Remove from resources
        resource_info = self.resources.pop(name)
        logger.info(f"Released resource: {name} (type: {resource_info.resource_type})")
        return True
    
    def release_all_resources(self):
        """Release all managed resources in dependency order."""
        # Create a copy of resource names to avoid modification during iteration
        resource_names = list(self.resources.keys())
        
        # Release in reverse dependency order
        released = set()
        max_iterations = len(resource_names) * 2  # Prevent infinite loops
        iterations = 0
        
        while resource_names and iterations < max_iterations:
            iterations += 1
            remaining = []
            
            for name in resource_names:
                # Check if this resource can be released
                can_release = True
                
                if not name in self.dependency_graph:
                    # No dependencies recorded
                    pass
                else:
                    # Check if any dependencies still exist
                    dependencies = self.dependency_graph[name]
                    for dep in dependencies:
                        if dep in self.resources and dep not in released:
                            can_release = False
                            break
                
                if can_release:
                    self.release_resource(name, force=True)
                    released.add(name)
                else:
                    remaining.append(name)
            
            resource_names = remaining
        
        # Force release any remaining resources
        if resource_names:
            logger.warning(f"Force releasing {len(resource_names)} remaining resources")
            for name in resource_names:
                self.release_resource(name, force=True)
    
    def get_resource_statistics(self) -> Dict[str, Any]:
        """Get statistics about managed resources.
        
        Returns:
            Dictionary with resource statistics
        """
        stats = {
            "total_resources": len(self.resources),
            "resource_types": {},
            "access_statistics": {},
            "creation_times": {}
        }
        
        # Group by resource type
        for name, info in self.resources.items():
            resource_type = info.resource_type
            if resource_type not in stats["resource_types"]:
                stats["resource_types"][resource_type] = 0
            stats["resource_types"][resource_type] += 1
            
            # Access statistics
            stats["access_statistics"][name] = {
                "access_count": info.access_count,
                "last_accessed": info.last_accessed.isoformat()
            }
            
            # Creation times
            stats["creation_times"][name] = info.created_at.isoformat()
        
        return stats


# Global resource manager instance
resource_manager = ResourceManager()


@contextmanager
def managed_resource(name: str, resource: Any, resource_type: str, finalizer: Optional[Callable] = None):
    """Context manager for temporarily managing a resource.
    
    Args:
        name: Name for the resource
        resource: The resource to manage
        resource_type: Type of resource
        finalizer: Optional cleanup function
    """
    resource_name = resource_manager.register_resource(name, resource, resource_type, finalizer)
    try:
        yield resource
    finally:
        resource_manager.release_resource(resource_name)


class ResourcePool:
    """Pool of reusable resources."""
    
    def __init__(self, resource_type: str, factory: Callable, max_size: int = 10):
        """Initialize resource pool.
        
        Args:
            resource_type: Type of resources in the pool
            factory: Function to create new resources
            max_size: Maximum size of the pool
        """
        self.resource_type = resource_type
        self.factory = factory
        self.max_size = max_size
        self.pool: list = []
        self.in_use: Dict[Any, datetime] = {}
        self.lock = asyncio.Lock()
        logger.info(f"ResourcePool initialized for {resource_type} (max_size: {max_size})")
    
    async def acquire(self, timeout: float = 30.0) -> Any:
        """Acquire a resource from the pool.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Resource from the pool
            
        Raises:
            asyncio.TimeoutError: If acquisition times out
        """
        async with self.lock:
            if self.pool:
                resource = self.pool.pop()
            else:
                # Create new resource
                resource = self.factory()
                resource_manager.register_resource(
                    f"{self.resource_type}_pool_{len(self.in_use)}",
                    resource,
                    self.resource_type,
                    metadata={"pool_managed": True}
                )
            
            self.in_use[resource] = datetime.utcnow()
            logger.debug(f"Acquired resource from pool: {self.resource_type}")
            return resource
    
    async def release(self, resource: Any):
        """Return a resource to the pool.
        
        Args:
            resource: Resource to return to the pool
        """
        async with self.lock:
            if resource in self.in_use:
                del self.in_use[resource]
                
                if len(self.pool) < self.max_size:
                    self.pool.append(resource)
                    logger.debug(f"Returned resource to pool: {self.resource_type}")
                else:
                    # Pool is full, release the resource
                    resource_name = None
                    for name, info in resource_manager.list_resources(self.resource_type).items():
                        if info.resource is resource:
                            resource_name = name
                            break
                    
                    if resource_name:
                        resource_manager.release_resource(resource_name)
                        logger.debug(f"Pool full, released resource: {self.resource_type}")
    
    def get_pool_statistics(self) -> Dict[str, Any]:
        """Get statistics about the pool.
        
        Returns:
            Dictionary with pool statistics
        """
        return {
            "resource_type": self.resource_type,
            "available": len(self.pool),
            "in_use": len(self.in_use),
            "max_size": self.max_size,
            "utilization": len(self.in_use) / self.max_size if self.max_size > 0 else 0
        }


# Health check utilities for resources
def health_check_resource(name: str, resource: Any) -> Dict[str, Any]:
    """Perform a basic health check on a resource.
    
    Args:
        name: Name of the resource
        resource: The resource to check
        
    Returns:
        Dictionary with health check results
    """
    try:
        # Try to determine resource health based on common patterns
        health_status = {
            "resource": name,
            "status": "unknown",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Check for common health indicators
        if hasattr(resource, 'ping'):
            # Try ping method
            resource.ping()
            health_status["status"] = "healthy"
        elif hasattr(resource, 'health'):
            # Try health property or method
            if callable(getattr(resource, 'health')):
                health = resource.health()
            else:
                health = getattr(resource, 'health')
            health_status["status"] = "healthy" if health else "unhealthy"
            health_status["details"] = health
        elif hasattr(resource, 'is_alive'):
            # Try is_alive method or property
            if callable(getattr(resource, 'is_alive')):
                alive = resource.is_alive()
            else:
                alive = getattr(resource, 'is_alive')
            health_status["status"] = "healthy" if alive else "unhealthy"
        elif hasattr(resource, 'status'):
            # Try status property or method
            if callable(getattr(resource, 'status')):
                status = resource.status()
            else:
                status = getattr(resource, 'status')
            health_status["status"] = "healthy" if status else "unhealthy"
            health_status["details"] = status
        else:
            # Basic existence check
            health_status["status"] = "exists"
            
        logger.debug(f"Health check for resource {name}: {health_status['status']}")
        return health_status
        
    except Exception as e:
        health_status = {
            "resource": name,
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
        logger.error(f"Health check failed for resource {name}: {e}")
        return health_status


def health_check_all_resources() -> Dict[str, Any]:
    """Perform health checks on all managed resources.
    
    Returns:
        Dictionary with overall health status and individual resource statuses
    """
    results = {}
    all_healthy = True
    
    for name, info in resource_manager.list_resources().items():
        try:
            result = health_check_resource(name, info.resource)
            results[name] = result
            if result["status"] not in ["healthy", "exists"]:
                all_healthy = False
        except Exception as e:
            results[name] = {
                "resource": name,
                "status": "error",
                "error": f"Failed to run health check: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
            all_healthy = False
            logger.error(f"Error running health check for resource {name}: {e}")
    
    overall_status = {
        "status": "healthy" if all_healthy else "unhealthy",
        "resources": results,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Overall resource health check status: {overall_status['status']}")
    return overall_status
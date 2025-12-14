#!/usr/bin/env python3
"""
Test script for AI Workbench v2 components.
"""

import sys
import os
import logging

# Add the project root to the path so we can import our packages
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all modules can be imported successfully."""
    logger.info("Testing imports...")
    
    try:
        from backend.services import (
            ChatProcessor,
            config,
            metrics_collector,
            performance_counters,
            resource_manager
        )
        # Other imports from separate modules
        from backend.services.pubnub_job_processor import JobProcessor, PubNubJobListener, create_pubnub_job_processor
        from backend.services.exceptions import (
            AiWorkbenchError,
            ConfigurationError,
            ServiceInitializationError,
            ProcessingError,
            NetworkError,
            AuthenticationError,
            RateLimitError,
            ValidationError
        )
        from backend.services.retry import retry_with_backoff, RetryConfig, API_RETRY_CONFIG, NETWORK_RETRY_CONFIG
        from backend.services.monitoring import monitored_operation, health_check_component, health_check_all_components
        from backend.services import cleanup_ai_workbench_components
        logger.info("✓ All imports successful")
        return True
    except Exception as e:
        logger.error(f"✗ Import failed: {e}")
        return False

def test_config():
    """Test configuration management."""
    logger.info("Testing configuration...")
    
    try:
        from backend.services.config import config
        logger.info(f"✓ Configuration loaded: DEFAULT_MODEL={config.DEFAULT_MODEL}")
        return True
    except Exception as e:
        logger.error(f"✗ Configuration test failed: {e}")
        return False

def test_exceptions():
    """Test custom exception classes."""
    logger.info("Testing custom exceptions...")
    
    try:
        from backend.services.exceptions import ProcessingError
        error = ProcessingError("test_operation", "test_reason", {"detail": "test"})
        assert error.operation == "test_operation"
        assert error.reason == "test_reason"
        assert error.details == {"detail": "test"}
        logger.info("✓ Custom exceptions working")
        return True
    except Exception as e:
        logger.error(f"✗ Custom exceptions test failed: {e}")
        return False

def test_retry_config():
    """Test retry configuration."""
    logger.info("Testing retry configuration...")
    
    try:
        from backend.services.retry import API_RETRY_CONFIG
        assert API_RETRY_CONFIG.max_attempts == 3
        assert API_RETRY_CONFIG.base_delay == 1.0
        logger.info("✓ Retry configuration working")
        return True
    except Exception as e:
        logger.error(f"✗ Retry configuration test failed: {e}")
        return False

def test_monitoring():
    """Test monitoring components."""
    logger.info("Testing monitoring components...")
    
    try:
        from backend.services.monitoring import metrics_collector, performance_counters
        # Test metrics collector
        operation_id = metrics_collector.start_operation("test_operation")
        metrics = metrics_collector.end_operation(operation_id)
        assert metrics is not None
        assert metrics.operation_name == "test_operation"
        
        # Test performance counters
        performance_counters.increment("test_counter")
        assert performance_counters.get_counter("test_counter") == 1
        
        logger.info("✓ Monitoring components working")
        return True
    except Exception as e:
        logger.error(f"✗ Monitoring components test failed: {e}")
        return False

def test_resource_management():
    """Test resource management components."""
    logger.info("Testing resource management...")
    
    try:
        from backend.services.resource_manager import resource_manager
        
        # Test resource registration
        test_resource = {"test": "data"}
        resource_name = resource_manager.register_resource(
            "test_resource", 
            test_resource, 
            "test_type"
        )
        
        # Test resource retrieval
        retrieved = resource_manager.get_resource(resource_name)
        assert retrieved == test_resource
        
        # Test resource release
        result = resource_manager.release_resource(resource_name)
        assert result == True
        
        logger.info("✓ Resource management working")
        return True
    except Exception as e:
        logger.error(f"✗ Resource management test failed: {e}")
        return False

def main():
    """Run all tests."""
    logger.info("Starting AI Workbench v2 tests...")
    
    tests = [
        test_imports,
        test_config,
        test_exceptions,
        test_retry_config,
        test_monitoring,
        test_resource_management
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    logger.info(f"Tests completed: {passed} passed, {failed} failed")
    
    if failed == 0:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
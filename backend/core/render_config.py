# backend/core/render_config.py - Render Platform Specific Configuration
"""
Render platform specific optimizations and configuration.
Free tier limitations: https://render.com/docs/free
"""

import os
import logging
from datetime import datetime
from fastapi import FastAPI
from typing import Tuple

logger = logging.getLogger(__name__)


def configure_for_render(app: FastAPI = None) -> bool:
    """
    Apply Render-specific optimizations based on environment.
    
    Args:
        app: FastAPI app instance for health check endpoint registration
        
    Returns:
        bool: True if running on Render, False otherwise
    """
    # Check if running on Render
    IS_RENDER = os.getenv('RENDER', '').lower() == 'true'
    
    if IS_RENDER:
        logger.info("Running on Render, applying optimizations...")
        
        # 1. Reduce connection pool size (Render free tier has limited memory)
        os.environ.setdefault('DATABASE_POOL_SIZE', '3')
        os.environ.setdefault('DATABASE_MAX_OVERFLOW', '2')
        
        # 2. Increase timeout settings
        os.environ.setdefault('REQUEST_TIMEOUT', '30')
        os.environ.setdefault('CONNECT_TIMEOUT', '10')
        
        # 3. Enable keepalive (prevent cold start timeouts)
        os.environ.setdefault('KEEPALIVE', 'true')
        
        # 4. Reduce log level (reduce IO)
        os.environ.setdefault('LOG_LEVEL', 'WARNING')
        
        # 5. Enable compression
        os.environ.setdefault('GZIP_COMPRESSION', 'true')
        
        # Note: Health check endpoint is now handled by the main application
        # We don't register a duplicate endpoint here
        
        logger.info("Render optimizations applied successfully")
        return True
    
    logger.info("Not running on Render, using default configuration")
    return False


def get_render_optimized_config() -> dict:
    """
    Get Render-optimized configuration values.
    
    Returns:
        dict: Configuration dictionary with optimized values
    """
    return {
        # Connection pool settings
        "pool_size": int(os.getenv('DATABASE_POOL_SIZE', '3')),
        "max_overflow": int(os.getenv('DATABASE_MAX_OVERFLOW', '2')),
        
        # Timeout settings
        "request_timeout": int(os.getenv('REQUEST_TIMEOUT', '30')),
        "connect_timeout": int(os.getenv('CONNECT_TIMEOUT', '10')),
        
        # Additional pool optimizations
        "pool_recycle": int(os.getenv('DB_POOL_RECYCLE', '300')),  # 5 minutes
        "pool_timeout": int(os.getenv('DB_POOL_TIMEOUT', '30')),
        
        # Feature flags
        "keepalive": os.getenv('KEEPALIVE', 'true').lower() == 'true',
        "gzip_compression": os.getenv('GZIP_COMPRESSION', 'true').lower() == 'true',
        
        # Logging
        "log_level": os.getenv('LOG_LEVEL', 'WARNING')
    }


def is_render_environment() -> bool:
    """
    Check if the application is running in Render environment.
    
    Returns:
        bool: True if running on Render, False otherwise
    """
    return os.getenv('RENDER', '').lower() == 'true'


def get_render_deployment_info() -> dict:
    """
    Get Render deployment information.
    
    Returns:
        dict: Deployment information
    """
    return {
        "is_render": is_render_environment(),
        "service_name": os.getenv('RENDER_SERVICE_NAME', 'unknown'),
        "region": os.getenv('RENDER_REGION', 'unknown'),
        "url": os.getenv('RENDER_EXTERNAL_URL', 'unknown')
    }
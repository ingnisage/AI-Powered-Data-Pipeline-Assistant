# backend/services/logging_service.py - Logging Service
"""
Centralized logging service with database persistence and real-time publishing.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from backend.models.logging import LogBuilder, PublishableLogEntry
from backend.utils.sanitization import sanitize_for_log, sanitize_for_display

logger = logging.getLogger(__name__)

class LoggingService:
    """Service for centralized logging with multiple outputs."""
    
    def __init__(self, supabase_client=None, pubnub_client=None):
        """Initialize logging service.
        
        Args:
            supabase_client: Supabase client for database logging
            pubnub_client: PubNub client for real-time logging
        """
        self.supabase_client = supabase_client
        self.pubnub_client = pubnub_client
        
        logger.info("LoggingService initialized")
    
    def save_log(
        self,
        level: str,
        message: str,
        source: str = "system",
        component: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Save log entry to database.
        
        Args:
            level: Log level (INFO, ERROR, etc.)
            message: Log message
            source: Log source
            component: Component name
            user_id: User identifier
            session_id: Session identifier
            duration_ms: Operation duration in milliseconds
            metadata: Additional metadata
        """
        # Sanitize message
        sanitized_message = sanitize_for_log(message)
        
        # Build log entry
        log_entry = LogBuilder.info(
            message=sanitized_message,
            source=source,
            component=component,
            user_id=user_id,
            session_id=session_id,
            duration_ms=duration_ms,
            metadata=metadata or {}
        )
        
        # Save to database
        if self.supabase_client:
            try:
                self.supabase_client.table("logs").insert(
                    log_entry.to_dict()
                ).execute()
            except Exception as e:
                logger.warning(f"Failed to save log to database: {e}")
    
    def publish_log(
        self,
        level: str,
        message: str,
        source: str = "system",
        component: Optional[str] = None,
        channel: str = "logs",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Publish log entry to real-time channel.
        
        Args:
            level: Log level
            message: Log message
            source: Log source
            component: Component name
            channel: PubNub channel
            metadata: Additional metadata
        """
        # Sanitize for display
        sanitized_message = sanitize_for_display(message)
        
        # Build publishable log entry
        log_entry = LogBuilder.publishable(
            message=sanitized_message,
            level=level,
            source=source,
            component=component,
            channel=channel,
            metadata=metadata or {}
        )
        
        # Publish to real-time channel
        if self.pubnub_client:
            try:
                self.pubnub_client.publish().channel(channel).message(
                    log_entry.to_publish_dict()
                ).pn_async(lambda r, s: None)
            except Exception as e:
                logger.warning(f"Failed to publish log: {e}")
    
    def log_and_publish(
        self,
        level: str,
        message: str,
        source: str = "system",
        component: Optional[str] = None,
        channel: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Save log to database and optionally publish to real-time channel.
        
        Args:
            level: Log level
            message: Log message
            source: Log source
            component: Component name
            channel: Optional PubNub channel
            user_id: User identifier
            session_id: Session identifier
            duration_ms: Operation duration in milliseconds
            metadata: Additional metadata
        """
        # Save to database
        self.save_log(
            level=level,
            message=message,
            source=source,
            component=component,
            user_id=user_id,
            session_id=session_id,
            duration_ms=duration_ms,
            metadata=metadata
        )
        
        # Publish if channel specified
        if channel:
            self.publish_log(
                level=level,
                message=message,
                source=source,
                component=component,
                channel=channel,
                metadata=metadata
            )

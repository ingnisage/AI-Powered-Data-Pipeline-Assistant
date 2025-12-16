# backend/services/config.py - Configuration Management
"""
Centralized configuration management for ai_workbench components.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


@dataclass
class AiWorkbenchConfig:
    """Configuration for ai_workbench components."""
    
    # API timeouts
    API_TIMEOUT_SHORT: int = 15
    API_TIMEOUT_LONG: int = 30
    API_TIMEOUT_TASK_OPS: int = 20  # Added missing timeout for task operations
    
    # Performance settings
    RERUN_THROTTLE_SECONDS: float = 0.5
    BATCH_PROCESS_LIMIT: int = 10
    
    # UI limits
    MAX_CHAT_HISTORY: int = 100
    MAX_LOG_ENTRIES: int = 50
    
    # Validation rules
    MIN_TASK_NAME_LENGTH: int = 3
    MAX_MESSAGE_LENGTH: int = 10000
    
    # PubNub settings
    PUBNUB_JOB_CHANNEL: str = "job-requests"
    PUBNUB_RESPONSE_CHANNEL: str = "job-responses"
    PUBNUB_SUBSCRIBE_KEY: str = os.getenv("PUBNUB_SUBSCRIBE_KEY", "demo")
    PUBNUB_PUBLISH_KEY: str = os.getenv("PUBNUB_PUBLISH_KEY", "demo")
    PUBNUB_CHANNELS: List[str] = field(default_factory=lambda: ["chat", "tasks", "logs"])
    
    # Timezone configuration
    DEFAULT_TIMEZONE: str = "America/New_York"
    AVAILABLE_TIMEZONES: Dict[str, str] = field(default_factory=lambda: {
        "US Eastern (EST/EDT)": "America/New_York",
        "US Pacific (PST/PDT)": "America/Los_Angeles",
        "US Central (CST/CDT)": "America/Chicago",
        "UTC": "UTC",
        "Europe/London": "Europe/London",
        "Asia/Tokyo": "Asia/Tokyo",
    })
    
    # UI Configuration
    MAX_SEARCH_RESULTS: int = 10  # Maximum search results to display
    MAX_LOGS_DISPLAY: int = 50  # Maximum logs to display in UI
    MAX_LOGS_STORED: int = 200  # Maximum logs to keep in session state
    MAX_CHAT_MESSAGES_DISPLAY: int = 10  # Maximum chat messages to display (changed from 50 to 10)
    
    # Input Validation Limits
    MAX_TASK_NAME_LENGTH: int = 200
    MAX_CHAT_MESSAGE_LENGTH: int = 5000
    MAX_SEARCH_QUERY_LENGTH: int = 500
    MIN_SEARCH_QUERY_LENGTH: int = 1  # Changed from 3 to 1 to allow shorter queries
    
    # Model settings
    DEFAULT_MODEL: str = "gpt-4o-mini"
    FALLBACK_MODEL: str = "gpt-4o-mini"
    
    # Retry settings
    MAX_RETRY_ATTEMPTS: int = 3
    BASE_RETRY_DELAY: float = 1.0
    MAX_RETRY_DELAY: float = 60.0
    
    # Rate limiting
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    MAX_REQUESTS_PER_WINDOW: int = 100
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    ENABLE_LOG_SANITIZATION: bool = True
    
    # Security settings
    ENABLE_INPUT_VALIDATION: bool = True
    ENABLE_OUTPUT_SANITIZATION: bool = True
    
    def __post_init__(self):
        """Validate configuration values after initialization."""
        self._validate_timeouts()
        self._validate_performance_settings()
        self._validate_validation_rules()
        self._validate_retry_settings()
        self._validate_rate_limiting()
        
        logger.info("AiWorkbenchConfig initialized and validated")
    
    def _validate_timeouts(self):
        """Validate timeout settings."""
        if self.API_TIMEOUT_SHORT <= 0:
            raise ValueError("API_TIMEOUT_SHORT must be positive")
        if self.API_TIMEOUT_LONG <= 0:
            raise ValueError("API_TIMEOUT_LONG must be positive")
        if self.API_TIMEOUT_TASK_OPS <= 0:  # Added validation for the new timeout
            raise ValueError("API_TIMEOUT_TASK_OPS must be positive")
        if self.API_TIMEOUT_SHORT > self.API_TIMEOUT_LONG:
            raise ValueError("API_TIMEOUT_SHORT cannot be greater than API_TIMEOUT_LONG")
    
    def _validate_performance_settings(self):
        """Validate performance settings."""
        if self.RERUN_THROTTLE_SECONDS < 0:
            raise ValueError("RERUN_THROTTLE_SECONDS must be non-negative")
        if self.BATCH_PROCESS_LIMIT <= 0:
            raise ValueError("BATCH_PROCESS_LIMIT must be positive")
    
    def _validate_validation_rules(self):
        """Validate validation rule settings."""
        if self.MIN_TASK_NAME_LENGTH <= 0:
            raise ValueError("MIN_TASK_NAME_LENGTH must be positive")
        if self.MAX_TASK_NAME_LENGTH <= 0:
            raise ValueError("MAX_TASK_NAME_LENGTH must be positive")
        if self.MIN_TASK_NAME_LENGTH > self.MAX_TASK_NAME_LENGTH:
            raise ValueError("MIN_TASK_NAME_LENGTH cannot be greater than MAX_TASK_NAME_LENGTH")
        if self.MAX_MESSAGE_LENGTH <= 0:
            raise ValueError("MAX_MESSAGE_LENGTH must be positive")
        if self.MAX_CHAT_MESSAGE_LENGTH <= 0:
            raise ValueError("MAX_CHAT_MESSAGE_LENGTH must be positive")
        if self.MAX_SEARCH_QUERY_LENGTH <= 0:
            raise ValueError("MAX_SEARCH_QUERY_LENGTH must be positive")
        if self.MIN_SEARCH_QUERY_LENGTH <= 0:
            raise ValueError("MIN_SEARCH_QUERY_LENGTH must be positive")
        if self.MIN_SEARCH_QUERY_LENGTH > self.MAX_SEARCH_QUERY_LENGTH:
            raise ValueError("MIN_SEARCH_QUERY_LENGTH cannot be greater than MAX_SEARCH_QUERY_LENGTH")
    
    def _validate_retry_settings(self):
        """Validate retry settings."""
        if self.MAX_RETRY_ATTEMPTS <= 0:
            raise ValueError("MAX_RETRY_ATTEMPTS must be positive")
        if self.BASE_RETRY_DELAY <= 0:
            raise ValueError("BASE_RETRY_DELAY must be positive")
        if self.MAX_RETRY_DELAY <= 0:
            raise ValueError("MAX_RETRY_DELAY must be positive")
        if self.BASE_RETRY_DELAY > self.MAX_RETRY_DELAY:
            raise ValueError("BASE_RETRY_DELAY cannot be greater than MAX_RETRY_DELAY")
    
    def _validate_rate_limiting(self):
        """Validate rate limiting settings."""
        if self.RATE_LIMIT_WINDOW_SECONDS <= 0:
            raise ValueError("RATE_LIMIT_WINDOW_SECONDS must be positive")
        if self.MAX_REQUESTS_PER_WINDOW <= 0:
            raise ValueError("MAX_REQUESTS_PER_WINDOW must be positive")
    
    @classmethod
    def from_env(cls) -> 'AiWorkbenchConfig':
        """Create configuration from environment variables.
        
        Returns:
            AiWorkbenchConfig instance with values from environment
        """
        return cls(
            API_TIMEOUT_SHORT=int(os.getenv("API_TIMEOUT_SHORT", "10")),
            API_TIMEOUT_LONG=int(os.getenv("API_TIMEOUT_LONG", "30")),
            API_TIMEOUT_TASK_OPS=int(os.getenv("API_TIMEOUT_TASK_OPS", "20")),  # Added missing env var
            RERUN_THROTTLE_SECONDS=float(os.getenv("RERUN_THROTTLE_SECONDS", "0.5")),
            BATCH_PROCESS_LIMIT=int(os.getenv("BATCH_PROCESS_LIMIT", "10")),
            MAX_CHAT_HISTORY=int(os.getenv("MAX_CHAT_HISTORY", "100")),
            MAX_LOG_ENTRIES=int(os.getenv("MAX_LOG_ENTRIES", "50")),
            MIN_TASK_NAME_LENGTH=int(os.getenv("MIN_TASK_NAME_LENGTH", "3")),
            MAX_TASK_NAME_LENGTH=int(os.getenv("MAX_TASK_NAME_LENGTH", "200")),
            MAX_MESSAGE_LENGTH=int(os.getenv("MAX_MESSAGE_LENGTH", "10000")),
            MAX_CHAT_MESSAGE_LENGTH=int(os.getenv("MAX_CHAT_MESSAGE_LENGTH", "5000")),
            MAX_SEARCH_QUERY_LENGTH=int(os.getenv("MAX_SEARCH_QUERY_LENGTH", "500")),
            MIN_SEARCH_QUERY_LENGTH=int(os.getenv("MIN_SEARCH_QUERY_LENGTH", "1")),
            PUBNUB_JOB_CHANNEL=os.getenv("PUBNUB_JOB_CHANNEL", "job-requests"),
            PUBNUB_RESPONSE_CHANNEL=os.getenv("PUBNUB_RESPONSE_CHANNEL", "job-responses"),
            PUBNUB_SUBSCRIBE_KEY=os.getenv("PUBNUB_SUBSCRIBE_KEY", "demo"),
            PUBNUB_PUBLISH_KEY=os.getenv("PUBNUB_PUBLISH_KEY", "demo"),
            DEFAULT_TIMEZONE=os.getenv("DEFAULT_TIMEZONE", "America/New_York"),
            DEFAULT_MODEL=os.getenv("DEFAULT_MODEL", "gpt-4o-mini"),
            FALLBACK_MODEL=os.getenv("FALLBACK_MODEL", "gpt-4o-mini"),
            MAX_RETRY_ATTEMPTS=int(os.getenv("MAX_RETRY_ATTEMPTS", "3")),
            BASE_RETRY_DELAY=float(os.getenv("BASE_RETRY_DELAY", "1.0")),
            MAX_RETRY_DELAY=float(os.getenv("MAX_RETRY_DELAY", "60.0")),
            RATE_LIMIT_WINDOW_SECONDS=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
            MAX_REQUESTS_PER_WINDOW=int(os.getenv("MAX_REQUESTS_PER_WINDOW", "100")),
            MAX_SEARCH_RESULTS=int(os.getenv("MAX_SEARCH_RESULTS", "10")),
            MAX_LOGS_DISPLAY=int(os.getenv("MAX_LOGS_DISPLAY", "50")),
            MAX_LOGS_STORED=int(os.getenv("MAX_LOGS_STORED", "200")),
            MAX_CHAT_MESSAGES_DISPLAY=int(os.getenv("MAX_CHAT_MESSAGES_DISPLAY", "10")),  # Changed from 50 to 10
            LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
            ENABLE_LOG_SANITIZATION=os.getenv("ENABLE_LOG_SANITIZATION", "true").lower() == "true",
            ENABLE_INPUT_VALIDATION=os.getenv("ENABLE_INPUT_VALIDATION", "true").lower() == "true",
            ENABLE_OUTPUT_SANITIZATION=os.getenv("ENABLE_OUTPUT_SANITIZATION", "true").lower() == "true",
        )


# Global configuration instance
config: AiWorkbenchConfig = AiWorkbenchConfig.from_env()
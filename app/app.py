# app.py - Streamlit AI Workbench Application
import streamlit as st
import requests
import os
import sys
from dotenv import load_dotenv
from queue import Queue
import time
from datetime import datetime
import threading
import uuid
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from dateutil import parser as date_parser

# Add the project root to Python path to ensure proper imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables from .env file
load_dotenv()

# Check if running on Render and apply optimizations
IS_RENDER = os.getenv('RENDER', '').lower() == 'true'

if IS_RENDER:
    # Reduce logging level to minimize IO on Render free tier
    logging.basicConfig(level=logging.WARNING)
    # Set cache TTL to shorter duration to reduce memory usage
    os.environ.setdefault('STREAMLIT_CACHE_TTL', '60')  # 1 minute
else:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

logger = logging.getLogger(__name__)
logger.info("Starting Streamlit AI Workbench application")
logger.info(f"Running on Render: {IS_RENDER}")

from backend.services.config import config  # Import centralized configuration

from app.api_client import WorkbenchAPI  # Import API client
from app.state_manager import TaskManager, MessageFormatter, LogManager  # Import state managers
from app.client_cache import ClientCache, get_cached_tasks, cache_tasks, get_cached_chat_history, cache_chat_history, clear_cache  # Import cache utilities

# Add time import for sleep functionality
import time

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9 fallback
    ZoneInfo = None

# =================================== LOGGING SETUP ===================================
# Configure logging for better error tracking and debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.info("Starting Streamlit AI Workbench application")

# =================================== THREAD-SAFE QUEUE MANAGER ===================================
# Global queue manager to handle multi-process/thread scenarios in Streamlit
_queue_lock = threading.Lock()
_message_queues = {}
_last_rerun_time = {}  # Track last rerun time per session to throttle reruns

# Cache timezone object for performance
_cached_timezone: Optional[Any] = None

def get_session_queue(session_id: str) -> Queue:
    """Thread-safe session queue retrieval/creation.
    
    Args:
        session_id: Unique session identifier
        
    Returns:
        Queue instance for the session
    """
    with _queue_lock:
        if session_id not in _message_queues:
            _message_queues[session_id] = Queue()
            logger.debug(f"Created new queue for session: {session_id}")
        return _message_queues[session_id]

def cleanup_session_queue(session_id: str) -> None:
    """Thread-safe session queue cleanup.
    
    Args:
        session_id: Unique session identifier
    """
    with _queue_lock:
        if session_id in _message_queues:
            # Drain the queue before removing
            queue = _message_queues[session_id]
            while not queue.empty():
                try:
                    queue.get_nowait()
                except:
                    break
            del _message_queues[session_id]
            logger.debug(f"Cleaned up queue for session: {session_id}")
        # Also cleanup rerun tracking
        if session_id in _last_rerun_time:
            del _last_rerun_time[session_id]

def should_rerun(session_id: str) -> bool:
    """Check if enough time has passed since last rerun (throttling).
    
    Args:
        session_id: Unique session identifier
        
    Returns:
        True if rerun is allowed, False if throttled
    """
    with _queue_lock:
        current_time = time.time()
        last_rerun = _last_rerun_time.get(session_id, 0)
        
        if current_time - last_rerun >= config.RERUN_THROTTLE_SECONDS:
            _last_rerun_time[session_id] = current_time
            return True
        return False

# =================================== HELPER FUNCTIONS ===================================
def cleanup_pubnub() -> None:
    """Cleanup PubNub connection. Call this on session end or reset."""
    if "pubnub" in st.session_state:
        try:
            st.session_state.pubnub.unsubscribe_all()
            st.session_state.pubnub.stop()
            logger.info("PubNub connection cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during PubNub cleanup: {e}")
        finally:
            del st.session_state.pubnub
            st.session_state.pubnub_started = False
    
    # Also cleanup the session queue
    if "session_id" in st.session_state:
        cleanup_session_queue(st.session_state.session_id)

st.set_page_config(page_title="AI Workbench - Data Pipeline Assistant", layout="wide")

st.title("🚀 AI Workbench")

# Determine backend URL - use RENDER environment variable if available, otherwise default to localhost
RENDER_BACKEND_URL = os.environ.get('RENDER_BACKEND_URL')
BACKEND_URL_ENV = os.environ.get('BACKEND_URL')  # Alternative environment variable name
PRODUCTION_BACKEND_URL = RENDER_BACKEND_URL or BACKEND_URL_ENV

if PRODUCTION_BACKEND_URL:
    DEFAULT_BACKEND_URL = PRODUCTION_BACKEND_URL
    logger.info(f"Using production backend URL from environment: {PRODUCTION_BACKEND_URL}")
else:
    DEFAULT_BACKEND_URL = "http://localhost:8000"
    logger.info("Using default localhost backend URL")

# Display backend URL information in a more user-friendly way
st.sidebar.markdown("### 🔌 Backend Connection")

# Show current backend configuration
current_backend_display = PRODUCTION_BACKEND_URL if PRODUCTION_BACKEND_URL else "http://localhost:8000"
backend_type = "Production" if PRODUCTION_BACKEND_URL else "Local Development"

st.sidebar.markdown(f"**{backend_type}**: `{current_backend_display}`")

# Check if we're using a test API key and warn the user
API_KEY = os.environ.get("BACKEND_API_KEY", "test-api-key")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "production").lower()

logger.info(f"Backend API Key loaded: {API_KEY[:8] if API_KEY != 'test-api-key' else 'test-key'}... (hidden for security)")
logger.info(f"Environment mode: {ENVIRONMENT}")

# In development mode, we don't require a valid API key
if ENVIRONMENT in ["development", "dev", "local"]:
    logger.info("Development mode: Using relaxed authentication")
    # In development mode, we can use a placeholder key
    if API_KEY == "test-api-key":
        API_KEY = "dev-key-12345"  # Match the default dev key in security.py
        logger.info("Development mode: Using default dev API key")
else:
    # In production mode, warn about invalid keys
    if API_KEY == "test-api-key":
        st.sidebar.error("⚠️ **Test API Key Detected**\n\nAuthentication may fail. Set `BACKEND_API_KEY` environment variable.")
        logger.warning("USING TEST API KEY - AUTHENTICATION MAY FAIL")
    else:
        logger.info("Using valid backend API key")

# Allow manual override - only show if user wants to change it
with st.sidebar.expander("⚙️ Advanced Settings"):
    st.markdown("#### Backend Configuration")
    API_URL = st.text_input("Override Backend URL", value=DEFAULT_BACKEND_URL, 
                           help="Manually override the backend URL if needed", key="backend_url_override")
    
    # Show current effective URL
    st.info(f"**Effective URL**: `{API_URL}`")

# Log the actual URL being used
logger.info(f"Backend URL configured as: {API_URL}")

# Performance settings in sidebar
with st.sidebar.expander("⚙️ Performance Settings"):
    st.caption(f"Rerun Throttle: {config.RERUN_THROTTLE_SECONDS}s")
    st.caption(f"Batch Size: {config.BATCH_PROCESS_LIMIT} messages")
    
    # Show cache statistics
    try:
        cache = ClientCache()
        stats = cache.get_stats()
        st.divider()
        st.caption("Cache Statistics")
        st.caption(f"Active Items: {stats['active_items']}")
        st.caption(f"Expired Items: {stats['expired_items']}")
        st.caption(f"Total Items: {stats['total_items']}")
        
        if st.button("🗑️ Clear Cache", key="clear_cache", use_container_width=True):
            clear_cache()
            st.success("Cache cleared!")
            time.sleep(0.5)
            st.rerun()
    except Exception as e:
        logger.error(f"Error displaying cache stats: {e}")

# Add cleanup button in sidebar
if st.sidebar.button("🔄 Reset Session", help="Clear session and cleanup connections"):
    logger.info("User initiated session reset")
    cleanup_pubnub()
    # Clear cache
    clear_cache()
    # Clear other session state
    for key in ["messages", "tasks", "session_id"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

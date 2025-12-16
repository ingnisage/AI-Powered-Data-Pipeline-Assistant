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

# Set the API URL in main scope
API_URL = DEFAULT_BACKEND_URL

# Allow manual override - only show if user wants to change it
with st.sidebar.expander("⚙️ Advanced Settings"):
    st.markdown("#### Backend Configuration")
    API_URL = st.text_input("Override Backend URL", value=DEFAULT_BACKEND_URL, 
                           help="Manually override the backend URL if needed", key="backend_url_override")
    
    # Show current effective URL
    st.info(f"**Effective URL**: `{API_URL}`")

# Log the actual URL being used
logger.info(f"Backend URL configured as: {API_URL}")

# Update the API key in environment for the API client
os.environ["BACKEND_API_KEY"] = API_KEY

# Initialize API client with the configured URL
api_client = WorkbenchAPI(API_URL)

# Test the API connection
try:
    # Test root endpoint by making a direct request
    logger.info(f"Testing connection to backend at: {API_URL}")
    response = requests.get(f"{API_URL}/", timeout=5)
    if response.status_code == 200:
        logger.info("Backend connection test successful")
    else:
        logger.error(f"Backend connection test failed with status {response.status_code}")
        st.sidebar.error(f"Backend connection failed with status {response.status_code}")
except requests.exceptions.ConnectionError as e:
    logger.error(f"Backend connection test failed: Cannot connect to backend at {API_URL}")
    st.sidebar.error(f"Cannot connect to backend at {API_URL}")
except requests.exceptions.Timeout as e:
    logger.error(f"Backend connection test failed: Timeout connecting to backend at {API_URL}")
    st.sidebar.error(f"Timeout connecting to backend at {API_URL}")
except Exception as e:
    logger.error(f"Backend connection test error: {e}")
    st.sidebar.error(f"Backend connection error: {e}")

# Initialize session state
# Use a fixed session ID for persistence across refreshes in development
# In production, this would be tied to user authentication
FIXED_SESSION_ID = "persistent_dev_session_12345"
if "session_id" not in st.session_state:
    st.session_state.session_id = FIXED_SESSION_ID
    logger.info(f"Initialized persistent session: {st.session_state.session_id}")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "tasks" not in st.session_state:
    st.session_state.tasks = []

# Add initialization for previous_input
if "previous_input" not in st.session_state:
    st.session_state.previous_input = ""

# Add flag to track if chat history has been loaded
if "chat_history_loaded" not in st.session_state:
    st.session_state.chat_history_loaded = False

# =================================== MAIN APPLICATION ===================================
# Create tabs for different functionalities (removed Logs tab as requested)
tab1, tab2, tab3 = st.tabs(["💬 Chat", "📋 Tasks", "🔍 Search"])

# =================================== CHAT TAB ===================================
with tab1:
    st.header("🤖 AI Assistant")
    
    # Load chat history from backend if not already loaded
    if "chat_history_loaded" not in st.session_state or not st.session_state.chat_history_loaded:
        try:
            with st.spinner("Loading chat history..."):
                logger.info(f"Loading chat history for session: {st.session_state.session_id}")
                
                # Fetch chat history from backend (limit to 10 messages to ensure we get at least 5 pairs)
                success, chat_history_data, error_msg = api_client.get_chat_history(
                    limit=10, 
                    session_id=st.session_state.session_id
                )
                
                logger.info(f"Chat history fetch result - Success: {success}, Data count: {len(chat_history_data) if chat_history_data else 0}")
                
                if success and chat_history_data:
                    logger.info(f"Raw chat history data sample: {chat_history_data[:2] if len(chat_history_data) > 0 else []}")
                    
                    # Convert chat history from backend format to UI format
                    converted_messages = MessageFormatter.convert_chat_history(chat_history_data)
                    logger.info(f"Converted messages count: {len(converted_messages)}")
                    logger.info(f"Converted messages sample: {converted_messages[:2] if len(converted_messages) > 0 else []}")
                    
                    # Sort messages by created_at timestamp if available
                    try:
                        # Sort by timestamp, oldest first (handle cases where created_at might be missing)
                        converted_messages.sort(key=lambda x: x.get('created_at', ''))
                        logger.info("Messages sorted by timestamp")
                        
                        # Take the most recent messages (last 6 for 3 pairs)
                        recent_messages = converted_messages[-6:] if len(converted_messages) > 6 else converted_messages
                        
                        # For display, we want newest at the top, so we reverse the order
                        display_messages = recent_messages[::-1]  # Reverse the list
                        
                        logger.info(f"After sorting and limiting: {len(display_messages)} messages for display")
                    except Exception as e:
                        logger.warning(f"Could not sort messages by timestamp: {e}")
                        # Fallback: just take the last 6 messages and reverse for display
                        recent_messages = converted_messages[-6:] if len(converted_messages) > 6 else converted_messages
                        display_messages = recent_messages[::-1]  # Reverse the list
                    
                    # Update session state with loaded messages
                    st.session_state.messages = display_messages
                    st.session_state.chat_history_loaded = True
                    logger.info(f"Loaded {len(display_messages)} chat messages from backend")
                else:
                    # If failed to load or no history, initialize with empty list
                    st.session_state.messages = []
                    st.session_state.chat_history_loaded = True
                    if error_msg:
                        logger.warning(f"Failed to load chat history: {error_msg}")
                        st.warning(f"Could not load chat history: {error_msg}")
                    else:
                        logger.info("No chat history found for this session")
                        # Also remove this informational message from UI
                        # st.info("No previous chat history found")
        except Exception as e:
            logger.error(f"Error loading chat history: {e}", exc_info=True)
            st.session_state.messages = []
            st.session_state.chat_history_loaded = True
            st.error(f"Error loading chat history: {e}")
    
    # Move the chat input to the top
    # Single chat input with both Enter key and Send button support
    # Check if backend is connected before enabling chat
    try:
        # Test backend connectivity for chat
        backend_connected = True  # We already tested this earlier
    except:
        backend_connected = False
    
    if backend_connected:
        # Create a form to contain both input and button
        with st.form(key="chat_form", clear_on_submit=True):
            # Text input for the message
            user_input = st.text_input(
                label="Your message",
                placeholder="Ask me anything about data pipelines...",
                label_visibility="collapsed"
            )
            
            # Submit button
            submit_button = st.form_submit_button("📤 Send Message", use_container_width=True)
            
            # Process the input when either Enter is pressed (submit_button is True) 
            # or when the form is submitted
            if submit_button and user_input and user_input.strip():
                prompt = user_input.strip()
                
                try:
                    # Add user message to chat history
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.markdown(prompt)
                    
                    # Get AI response
                    with st.chat_message("assistant"):
                        with st.spinner("Thinking..."):
                            success, response_data, error_msg = api_client.send_chat_message(
                                message=prompt,
                                system_prompt="general",
                                use_tools=True,
                                session_id=st.session_state.session_id  # Pass session_id for chat history tracking
                            )
                            
                            if success and response_data:
                                # Extract answer and tools used
                                answer = response_data.get("answer", "No response received.")
                                tools_used = response_data.get("tools_used", [])
                                
                                # Display response
                                st.markdown(answer)
                                
                                # Display tools used if any
                                if tools_used:
                                    with st.expander("Tools Used"):
                                        st.write(", ".join(tools_used))
                                
                                # Add assistant response to chat history
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": answer,
                                    "tools_used": tools_used
                                })
                                
                                # Clear the task cache to force refresh when switching to tasks tab
                                # This ensures newly created tasks from chat interactions appear
                                clear_cache(cache_type="tasks")
                                
                                # Show a notification that a task was created
                                st.success("✅ Task created from your chat message!")
                            else:
                                st.error(f"Failed to get response: {error_msg or 'Unknown error'}")
                except Exception as e:
                    logger.error(f"Error in chat processing: {e}", exc_info=True)
                    st.error(f"Error processing your message: {e}")
    else:
        st.warning("⚠️ Backend connection unavailable. Chat functionality disabled.")
    
    # Display chat messages (moved to bottom)
    st.subheader("Chat History")
    try:
        logger.info(f"Displaying {len(st.session_state.messages)} chat messages")
        # Display messages in the order they're stored (newest first)
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                # Display tools used if available
                if "tools_used" in message and message["tools_used"]:
                    with st.expander("Tools Used"):
                        st.write(", ".join(message["tools_used"]))
    except Exception as e:
        logger.error(f"Error displaying chat messages: {e}", exc_info=True)
        st.error(f"Error displaying chat messages: {e}")

# =================================== TASKS TAB ===================================
with tab2:
    st.header("📋 Task Management")
    
    # Task creation form
    with st.form("create_task_form"):
        task_name = st.text_input("Task Name")
        submitted = st.form_submit_button("Create Task")
        
        if submitted and task_name:
            with st.spinner("Creating task..."):
                success, task_data, error_msg = api_client.create_task(name=task_name)
                if success and task_data:
                    st.success(f"Task '{task_name}' created successfully!")
                    # Refresh tasks list
                    st.session_state.tasks = []  # Clear cache to force refresh
                    st.rerun()
                else:
                    st.error(f"Failed to create task: {error_msg or 'Unknown error'}")
    
    st.divider()
    
    # Display tasks
    st.subheader("Existing Tasks")
    
    with st.spinner("Loading tasks..."):
        # Use client-side caching for tasks
        cached_tasks = get_cached_tasks()
        if cached_tasks is None:
            success, tasks_data, error_msg = api_client.get_tasks()
            if success and tasks_data:
                # Cache the tasks
                cache_tasks(tasks_data)
                cached_tasks = tasks_data
            else:
                st.error(f"Failed to load tasks: {error_msg or 'Unknown error'}")
                cached_tasks = []
        
        if cached_tasks:
            # Sort and deduplicate tasks
            sorted_tasks = TaskManager.sort_tasks(TaskManager.deduplicate(cached_tasks))
            
            # Display tasks in a table
            for task in sorted_tasks:
                # Get the updated timestamp for display next to task title
                updated_at = task.get('updated_at', '')
                formatted_timestamp = MessageFormatter.format_timestamp(updated_at) if updated_at else ''
                
                # Create task title with timestamp aligned to the right
                task_title = f"**{task['name']}** - {task['status']} ({task['progress']}%)"
                if formatted_timestamp:
                    # Display timestamp next to task title
                    task_display = f"{task_title}  \n*Updated: {formatted_timestamp}*"
                else:
                    task_display = task_title
                
                with st.expander(task_display):
                    st.write(f"**ID:** {task['id']}")
                    st.write(f"**Description:** {task.get('description', 'No description')}")
                    st.write(f"**Priority:** {task.get('priority', 'Medium')}")
                    st.write(f"**Assigned To:** {task.get('assigned_to', 'Unassigned')}")
                    st.write(f"**Created:** {MessageFormatter.format_timestamp(task.get('created_at', ''))}")
                    st.write(f"**Updated:** {MessageFormatter.format_timestamp(task.get('updated_at', ''))}")
        else:
            st.info("No tasks found.")

# =================================== SEARCH TAB ===================================
with tab3:
    st.header("🔍 Knowledge Search")
    
    # Search form
    with st.form("search_form"):
        query = st.text_input("Search Query", placeholder="Enter your search query...")
        source = st.selectbox("Source", ["all", "github", "stackoverflow", "official_doc", "spark_docs"])
        max_results = st.slider("Max Results", 1, 10, 5)
        submitted = st.form_submit_button("Search")
        
        if submitted and query:
            with st.spinner("Searching..."):
                success, search_results, error_msg = api_client.search_knowledge(
                    query=query,
                    source=source,
                    max_results=max_results
                )
                
                if success and search_results:
                    st.subheader(f"Search Results ({search_results.get('total_results', 0)} found)")
                    
                    # Display search results
                    results = search_results.get("results", [])
                    if results:
                        for i, result in enumerate(results, 1):
                            with st.expander(f"{i}. {result.get('title', 'Untitled')}"):
                                st.markdown(f"**Source:** {result.get('source', 'Unknown')}")
                                st.markdown(f"**URL:** [{result.get('url', 'N/A')}]({result.get('url', '#')})")
                                st.markdown(f"**Snippet:** {result.get('snippet', 'No snippet available')}")
                    else:
                        st.info("No results found for your query.")
                else:
                    st.error(f"Search failed: {error_msg or 'Unknown error'}")

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

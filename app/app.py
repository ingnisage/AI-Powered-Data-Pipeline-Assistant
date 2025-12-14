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

from backend.services.config import config  # Import centralized configuration

from app.api_client import WorkbenchAPI  # Import API client
from app.state_manager import TaskManager, MessageFormatter, LogManager  # Import state managers

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9 fallback
    ZoneInfo = None

load_dotenv()

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

API_URL = st.sidebar.text_input("Backend URL", "http://localhost:8000")

# Performance settings in sidebar
with st.sidebar.expander("⚙️ Performance Settings"):
    st.caption(f"Rerun Throttle: {config.RERUN_THROTTLE_SECONDS}s")
    st.caption(f"Batch Size: {config.BATCH_PROCESS_LIMIT} messages")
    
    # Show queue status
    if "session_id" in st.session_state:
        queue = get_session_queue(st.session_state.session_id)
        queue_size = queue.qsize()
        if queue_size > 0:
            st.info(f"📨 Pending messages: {queue_size}")
        else:
            st.success("✓ All messages processed")

# Display settings in sidebar
with st.sidebar.expander("🌍 Display Settings"):
    # Timezone preference - use config
    selected_tz_label = st.selectbox(
        "Timezone",
        options=list(config.AVAILABLE_TIMEZONES.keys()),
        index=0,
        help="Timezone for displaying timestamps"
    )
    
    # Store selected timezone in session state
    if "timezone" not in st.session_state:
        st.session_state.timezone = config.AVAILABLE_TIMEZONES[selected_tz_label]
    elif config.AVAILABLE_TIMEZONES[selected_tz_label] != st.session_state.timezone:
        st.session_state.timezone = config.AVAILABLE_TIMEZONES[selected_tz_label]
        # Clear cached timezone when changed - reset global cache
        MessageFormatter.reset_timezone_cache()
        logger.info(f"Timezone changed to: {st.session_state.timezone}")

# Add cleanup button in sidebar
if st.sidebar.button("🔄 Reset Session", help="Clear session and cleanup connections"):
    logger.info("User initiated session reset")
    cleanup_pubnub()
    # Clear other session state
    for key in ["messages", "tasks", "session_id"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# =================================== SESSION MANAGEMENT ===================================
# Generate or retrieve unique session ID
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    logger.info(f"New session created: {st.session_state.session_id}")

# Initialize API client
if "api_client" not in st.session_state:
    st.session_state.api_client = WorkbenchAPI(API_URL)
    logger.info(f"API client initialized for: {API_URL}")

# Get the thread-safe queue for this session
session_queue = get_session_queue(st.session_state.session_id)

# Ensure our lists always exist
for key in ["messages", "tasks"]:
    if key not in st.session_state:
        st.session_state[key] = []

# Initialize tasks_updated_at timestamp for cache invalidation
if "tasks_updated_at" not in st.session_state:
    st.session_state.tasks_updated_at = time.time()

# =================================== INPUT VALIDATION ===================================
def validate_task_name(name: str) -> Tuple[bool, str]:
    """Validate task name input.
    
    Args:
        name: Task name to validate
        
    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    if not name or not name.strip():
        return False, "Task name cannot be empty"
    
    if len(name) > config.MAX_TASK_NAME_LENGTH:
        return False, f"Task name too long (max {config.MAX_TASK_NAME_LENGTH} characters)"
    
    if name.strip() != name:
        return False, "Task name has leading/trailing whitespace"
    
    # Check for potentially dangerous characters
    forbidden_chars = ['<', '>', '{', '}', '\x00']
    if any(char in name for char in forbidden_chars):
        return False, "Task name contains invalid characters"
    
    return True, ""


def validate_chat_message(message: str) -> Tuple[bool, str]:
    """Validate chat message input.
    
    Args:
        message: Chat message to validate
        
    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    if not message or not message.strip():
        return False, "Message cannot be empty"
    
    if len(message) > config.MAX_CHAT_MESSAGE_LENGTH:
        return False, f"Message too long (max {config.MAX_CHAT_MESSAGE_LENGTH} characters)"
    
    # Check for null bytes which can cause issues
    if '\x00' in message:
        return False, "Message contains invalid characters"
    
    return True, ""


def validate_search_query(query: str) -> Tuple[bool, str]:
    """Validate search query input.
    
    Args:
        query: Search query to validate
        
    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    if not query or not query.strip():
        return False, "Search query cannot be empty"
    
    if len(query) > config.MAX_SEARCH_QUERY_LENGTH:
        return False, f"Search query too long (max {config.MAX_SEARCH_QUERY_LENGTH} characters)"
    
    if len(query.strip()) < config.MIN_SEARCH_QUERY_LENGTH:
        return False, f"Search query too short (min {config.MIN_SEARCH_QUERY_LENGTH} characters)"
    
    # Check for null bytes
    if '\x00' in query:
        return False, "Query contains invalid characters"
    
    return True, ""


def deduplicate_tasks(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate tasks by ID, preserving order.
    
    Deprecated: Use TaskManager.deduplicate() instead.
    Kept for backward compatibility.
    """
    return TaskManager.deduplicate(tasks)


def _upsert_task_in_state(new_task: Dict[str, Any]) -> None:
    """Insert or update a task in st.session_state.tasks by `id`, avoiding duplicates.
    
    Args:
        new_task: Task dictionary to insert or update
    """
    st.session_state.tasks = TaskManager.upsert_task(st.session_state.tasks, new_task)
    st.session_state.tasks_updated_at = time.time()  # Invalidate cache


# =================================== PubNub Setup — ONLY puts into queue ===================================
if "pubnub" not in st.session_state:
    from pubnub.pnconfiguration import PNConfiguration
    from pubnub.pubnub import PubNub
    from pubnub.callbacks import SubscribeCallback

    pnconfig = PNConfiguration()
    pnconfig.subscribe_key = os.getenv("PUBNUB_SUBSCRIBE_KEY", config.PUBNUB_SUBSCRIBE_KEY)
    pnconfig.uuid = f"streamlit-client-{st.session_state.session_id}"
    pnconfig.ssl = True

    # --- IMPROVED THREAD-SAFE SECTION STARTS ---
    class QueueOnlyListener(SubscribeCallback):
        """Thread-safe listener that uses global queue manager."""
        def __init__(self, session_id: str):
            self.session_id = session_id

        def message(self, pubnub, event):
            # Get the queue through the thread-safe manager
            # This prevents stale reference issues
            try:
                queue = get_session_queue(self.session_id)
                queue.put({
                    "channel": event.channel,
                    "data": event.message
                })
                logger.debug(f"Message enqueued from channel: {event.channel}")
            except Exception as e:
                logger.error(f"Error enqueueing message: {e}")

    pubnub = PubNub(pnconfig)
    # Pass session ID instead of direct queue reference
    pubnub.add_listener(QueueOnlyListener(st.session_state.session_id))
    # --- IMPROVED THREAD-SAFE SECTION ENDS ---

    pubnub.subscribe().channels(config.PUBNUB_CHANNELS).execute()
    
    # Store PubNub instance for reuse and cleanup
    st.session_state.pubnub = pubnub
    st.session_state.pubnub_started = True

# =================================== PROCESS QUEUE SAFELY (main thread only) ===================================
def process_incoming_messages() -> None:
    """Process messages from the thread-safe queue with batching and throttling.
    
    Processes up to BATCH_PROCESS_LIMIT messages from the queue and updates
    session state. Implements smart rerun logic with throttling to avoid
    excessive page reloads.
    """
    # Get the current session's queue
    queue = get_session_queue(st.session_state.session_id)
    
    # Batch processing - process multiple messages before rerunning
    messages_processed: int = 0
    has_updates: bool = False
    
    # Process up to BATCH_PROCESS_LIMIT messages in one go
    while not queue.empty() and messages_processed < config.BATCH_PROCESS_LIMIT:
        try:
            item = queue.get_nowait()
            channel: str = item["channel"]
            data: Dict[str, Any] = item["data"]

            if channel == "chat" and isinstance(data, dict) and "content" in data:
                st.session_state.messages.append({"role": "assistant", "content": data["content"]})
                has_updates = True

            elif channel == "tasks" and isinstance(data, dict):
                if data.get("type") == "created":
                    _upsert_task_in_state(data.get("task"))
                elif data.get("type") == "updated":
                    _upsert_task_in_state(data.get("task"))
                has_updates = True

            # Logs channel processing removed as per user request
            
            messages_processed += 1
            
        except Exception as e:
            logger.error(f"Error processing message from channel {item.get('channel', 'unknown')}: {e}")
            break

    # Only rerun if:
    # 1. There are updates AND
    # 2. Either queue is empty (all messages processed) OR enough time has passed
    if has_updates:
        if queue.empty():
            # All messages processed, rerun immediately
            st.rerun()
        elif should_rerun(st.session_state.session_id):
            # Throttle: only rerun if enough time has passed
            st.rerun()
        # Otherwise, wait for next refresh cycle (updates are in state, just not visible yet)

# Run it every time the app refreshes
process_incoming_messages()

# Deprecated: These functions moved to state_manager.py
# Keeping references for backward compatibility
get_timezone = MessageFormatter.get_timezone
reset_timezone_cache = MessageFormatter.reset_timezone_cache
format_time_eastern = MessageFormatter.format_timestamp

# Initial task load using API client
if not st.session_state.tasks:
    success, tasks, error = st.session_state.api_client.get_tasks()
    if success:
        st.session_state.tasks = TaskManager.deduplicate(tasks)
        st.session_state.tasks_updated_at = time.time()
    elif error and "connect" not in error.lower():
        st.warning(f"⚠️ {error}")

# Initial logs load removed as per user request

# Initial chat history load using API client
if not st.session_state.messages:
    success, messages, error = st.session_state.api_client.get_chat_history(limit=10)
    if success:
        st.session_state.messages = MessageFormatter.convert_chat_history(messages)

# =================================== UI ===================================
tab1, tab2, tab3 = st.tabs(["Chat", "Search", "Tasks"])

# 在 tab1 部分替换为以下代码：
with tab1:
    st.header("Chat")
    
    # System prompt selection
    col1, col2 = st.columns([2, 1])
    with col1:
        system_prompt = st.selectbox(
            "AI Role",
            options=["data_engineer", "ml_engineer", "analyst"],
            format_func=lambda x: x.replace("_", " ").title(),
            key="system_prompt"
        )
    with col2:
        use_tools = st.checkbox("Enable Tools", value=True, key="use_tools")
    
    # Chat input at the top using a form
    with st.form("chat_form", clear_on_submit=True):
        prompt = st.text_input("Type a message...", key="chat_input", placeholder="Ask a question or describe an error...")
        submitted = st.form_submit_button("Send", use_container_width=True)
        
        if submitted and prompt:
            # Validate chat message input
            is_valid, error_msg = validate_chat_message(prompt)
            if not is_valid:
                st.error(f"❌ Invalid input: {error_msg}")
            else:
                # Add user message
                st.session_state.messages.append({"role": "user", "content": prompt})
                
                # Send to backend with loading indicator
                with st.spinner("🤔 Thinking..."):
                    success, data, error = st.session_state.api_client.send_chat_message(
                        message=prompt,
                        system_prompt=system_prompt,
                        use_tools=use_tools,
                        search_source=None
                    )
                
                if success and data:
                    # Add assistant response with tool info
                    assistant_msg = {
                        "role": "assistant",
                        "content": data.get("answer", "")
                    }
                    if "tools_used" in data:
                        assistant_msg["tools_used"] = data["tools_used"]
                    
                    st.session_state.messages.append(assistant_msg)
                    st.toast("✅ Response received!", icon="✅")
                    time.sleep(0.3)  # Brief delay for toast visibility
                    st.rerun()
                else:
                    st.error(f"❌ {error}")
    
    # Display chat messages below the input (newest first at top)
    # Limit to last 50 messages to avoid performance issues with large histories
    st.divider()
    
    # Optimized iteration: slice to last N messages, then reverse
    recent_messages = st.session_state.messages[-config.MAX_CHAT_MESSAGES_DISPLAY:] if len(st.session_state.messages) > config.MAX_CHAT_MESSAGES_DISPLAY else st.session_state.messages
    
    for msg in reversed(recent_messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # Show tools used if available
            if msg.get("tools_used"):
                st.caption(f"🛠️ Tools used: {', '.join(msg['tools_used'])}")
    
    # Show info if messages were truncated
    if len(st.session_state.messages) > config.MAX_CHAT_MESSAGES_DISPLAY:
        st.info(f"ℹ️ Showing last {config.MAX_CHAT_MESSAGES_DISPLAY} of {len(st.session_state.messages)} messages for performance")

with tab2:
    st.header("Search")
    
    st.markdown("### Search Knowledge Sources")
    st.markdown("Search across StackOverflow, GitHub, and official documentation for solutions and examples.")
    
    # Search source dropdown
    search_source_label = st.selectbox(
        "Search Source",
        options=["StackOverflow", "GitHub", "Spark Docs"],
        index=0,
        key="search_source",
        help="Select which knowledge source to search"
    )
    
    # Map dropdown labels to backend values
    search_source_map = {
        "StackOverflow": "stackoverflow",
        "GitHub": "github",
        "Spark Docs": "official_doc"
    }
    search_source = search_source_map.get(search_source_label)
    
    # Search input using a form
    with st.form("search_form", clear_on_submit=False):
        search_query = st.text_input(
            "Search Query",
            key="search_input",
            placeholder="e.g., 'how to handle null values in pandas' or 'spark dataframe join example'"
        )
        
        col1, col2 = st.columns([3, 1])
        with col1:
            max_results = st.slider("Max Results", min_value=1, max_value=config.MAX_SEARCH_RESULTS, value=5, key="max_results")
        with col2:
            search_submitted = st.form_submit_button("Search", use_container_width=True, type="primary")
    
    if search_submitted and search_query:
        # Validate search query input
        is_valid, error_msg = validate_search_query(search_query)
        if not is_valid:
            st.error(f"❌ Invalid search query: {error_msg}")
        else:
            # Show search status with spinner
            with st.spinner(f"🔍 Searching {search_source_label}..."):
                success, data, error = st.session_state.api_client.search_knowledge(
                    query=search_query,
                    source=search_source,
                    max_results=max_results
                )
            
            if success and data:
                results = data.get("results", [])
                total_results = data.get("total_results", 0)
                
                st.success(f"✅ Found {total_results} results")
                
                # Display results
                if results:
                    for i, result in enumerate(results, 1):
                        with st.expander(f"{i}. {result.get('title', 'Untitled')}"):
                            st.markdown(f"**Source:** {result.get('source', 'Unknown')} | [🔗 Link]({result.get('url', '#')})")
                            st.markdown(f"**Content:** {result.get('content', 'No content available')}")
                            if result.get('metadata'):
                                with st.expander("📋 Metadata"):
                                    st.json(result.get('metadata'))
                else:
                    st.info("No results found for your query.")
            else:
                st.error(f"❌ {error}")
    
    # Example searches
    st.divider()
    st.markdown("### Popular Searches")
    example_searches = [
        "How to handle missing values in pandas DataFrame?",
        "Apache Spark SQL join examples",
        "Python asyncio best practices",
    ]
    
    for example in example_searches:
        if st.button(example, key=f"example_{example}"):
            st.session_state.search_input = example
            st.rerun()

with tab3:
    st.header("Task Board")
    col1, col2, col3 = st.columns(3)  # Changed back to 3 columns since we're removing "Not Started" from header
    col1.metric("In Progress", len([t for t in st.session_state.tasks if t.get("status") == "In Progress"]))
    col2.metric("Completed", len([t for t in st.session_state.tasks if t.get("status") == "Completed"]))
    col3.metric("Total", len(st.session_state.tasks))

    # Use a form to create tasks; `clear_on_submit=True` will reset the input safely
    with st.form("create_task_form", clear_on_submit=True):
        new_name = st.text_input("New task", key="new_task_name", placeholder="Enter task name...")
        submitted = st.form_submit_button("Create", use_container_width=True, type="primary")

        if submitted:
            # Validate task name input
            is_valid, error_msg = validate_task_name(new_name)
            if not is_valid:
                st.error(f"❌ {error_msg}")
            else:
                # Sanitize input by stripping whitespace
                sanitized_name = new_name.strip()
                
                # Create task with loading indicator
                with st.spinner("Creating task..."):
                    success, task, error = st.session_state.api_client.create_task(sanitized_name)
                
                if success:
                    if task:
                        _upsert_task_in_state(task)
                    else:
                        # Fallback: refresh task list
                        success_refresh, tasks, _ = st.session_state.api_client.get_tasks()
                        if success_refresh:
                            st.session_state.tasks = TaskManager.deduplicate(tasks)
                    
                    st.toast(f"✅ Task '{sanitized_name}' created!", icon="✅")
                    time.sleep(0.3)  # Brief delay for toast visibility
                    st.rerun()
                else:
                    st.error(f"❌ {error}")

    # Remove "Not Started" from options as it causes database constraint violations
    status_options = ["In Progress", "Completed", "Failed"]

    # Empty state
    if not st.session_state.tasks:
        st.info("📋 No tasks yet. Create your first task above!")
    else:
        # Sort tasks so that top shows In Progress, then others
        status_order: Dict[str, int] = {
        "In Progress": 1,
        "Completed": 2,
        "Failed": 3,
    }

    def _task_sort_key(t: Dict[str, Any]) -> tuple:
        """Sort key function for tasks.
        
        Args:
            t: Task dictionary
            
        Returns:
            Tuple of (status_priority, created_at, name) for sorting
        """
        s = t.get("status") or ""
        return (status_order.get(s, 99), t.get("created_at") or "", t.get("name") or "")

    @st.cache_data
    def get_sorted_tasks(tasks_tuple: tuple, timestamp: float) -> List[Dict[str, Any]]:
        """Cache sorted tasks. Update timestamp to invalidate cache.
        
        Args:
            tasks_tuple: Tuple of task dictionaries (for hashability)
            timestamp: Timestamp for cache invalidation
            
        Returns:
            Sorted list of task dictionaries
        """
        # Convert tuples back to dictionaries for sorting
        tasks_list = [dict(t) for t in tasks_tuple]
        return sorted(tasks_list, key=_task_sort_key)

    # Use cached sorting - converts to tuple for hashability
    # Convert each task dict to a tuple of its items for hashability
    tasks_as_tuples = tuple(tuple(sorted(t.items())) for t in st.session_state.tasks)
    sorted_tasks_tuples = get_sorted_tasks(
        tasks_as_tuples,
        st.session_state.get("tasks_updated_at", time.time())
    )
    # Convert back to list of dicts
    sorted_tasks: List[Dict[str, Any]] = [dict(t) for t in sorted_tasks_tuples]

    # Track which task expander was last interacted with to keep it open
    last_interacted_task = st.session_state.get("last_interacted_task", None)
    
    for task in sorted_tasks:
        task_id = task.get("id")
        task_name = task.get("name", "Unnamed Task")
        current_status = task.get("status", "Not Started")
        current_progress = int(task.get("progress", 0) or 0)

        # Determine if this expander should be expanded
        is_expanded = False
        if last_interacted_task == task_id:
            is_expanded = True
            
        # Format task creation timestamp for display
        created_at_raw = task.get("created_at", "")
        if created_at_raw:
            user_tz = st.session_state.get("timezone", config.DEFAULT_TIMEZONE)
            formatted_time = MessageFormatter.format_timestamp(created_at_raw, tz_name=user_tz)
            # Extract just the date and time part without timezone name for cleaner display
            time_part = formatted_time.split(' ')[0:2]  # Get date and time only
            display_time = ' '.join(time_part)
        else:
            display_time = "Unknown time"
        
        with st.expander(f"{task_name} — {current_status} ({display_time})", expanded=is_expanded):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.write(task.get("description", ""))
                # Ensure current status is in options, fallback to first option if not found
                current_status_index = 0
                if current_status in status_options:
                    current_status_index = status_options.index(current_status)
                else:
                    logger.warning(f"Task {task_id} has invalid status: {current_status}")
                
                # Use session state to track values and prevent unwanted re-renders
                status_key = f"status_{task_id}"
                progress_key = f"progress_{task_id}"
                
                # Initialize session state for this task if not exists
                if status_key not in st.session_state:
                    st.session_state[status_key] = current_status
                if progress_key not in st.session_state:
                    st.session_state[progress_key] = current_progress
                
                # Create a unique callback function for this task to avoid closure issues
                def make_status_callback(status_key, temp_key, task_id):
                    def update_status():
                        if temp_key in st.session_state:
                            logger.info(f"Status callback triggered: {temp_key} -> {status_key}, value: {st.session_state[temp_key]}")
                            st.session_state[status_key] = st.session_state[temp_key]
                            st.session_state["last_interacted_task"] = task_id
                            logger.info(f"Session state updated: {status_key} = {st.session_state[status_key]}")
                    return update_status
                
                def make_progress_callback(progress_key, temp_key, task_id):
                    def update_progress():
                        if temp_key in st.session_state:
                            logger.info(f"Progress callback triggered: {temp_key} -> {progress_key}, value: {st.session_state[temp_key]}")
                            st.session_state[progress_key] = st.session_state[temp_key]
                            st.session_state["last_interacted_task"] = task_id
                            logger.info(f"Session state updated: {progress_key} = {st.session_state[progress_key]}")
                    return update_progress
                
                # Create temporary keys for the widgets
                temp_status_key = f"_status_{task_id}"
                temp_progress_key = f"_progress_{task_id}"
                
                new_status = st.selectbox(
                    "Status",
                    options=status_options,
                    index=status_options.index(st.session_state[status_key]) if st.session_state[status_key] in status_options else 0,
                    key=temp_status_key,
                    on_change=make_status_callback(status_key, temp_status_key, task_id)
                )
                
                new_progress = st.slider(
                    "Progress", 
                    min_value=0, 
                    max_value=100, 
                    value=st.session_state[progress_key], 
                    key=temp_progress_key,
                    on_change=make_progress_callback(progress_key, temp_progress_key, task_id)
                )

            with col_b:
                if st.button("Update", key=f"update_{task_id}"):
                    if not task_id:
                        st.error("Cannot update task without an ID")
                    else:
                        # Set this task as last interacted before updating
                        st.session_state["last_interacted_task"] = task_id
                        
                        # Use the values from session state
                        final_status = st.session_state[status_key]
                        final_progress = st.session_state[progress_key]
                        
                        # Log the update attempt for debugging
                        logger.info(f"Attempting to update task {task_id}: status='{final_status}', progress={final_progress}")
                        logger.info(f"Current session state - status: {st.session_state.get(status_key, 'NOT_FOUND')}, progress: {st.session_state.get(progress_key, 'NOT_FOUND')}")
                        
                        # Validate status before sending to backend
                        valid_statuses = ["In Progress", "Completed", "Failed"]
                        if final_status not in valid_statuses:
                            st.error(f"Invalid status '{final_status}'. Must be one of: {valid_statuses}")
                        else:
                            # Update task with loading indicator
                            with st.spinner("Updating task..."):
                                success, error = st.session_state.api_client.update_task(
                                    task_id=task_id,
                                    status=final_status,
                                    progress=final_progress
                                )
                        
                        if success:
                            # Refresh task list
                            success_refresh, tasks, _ = st.session_state.api_client.get_tasks()
                            if success_refresh:
                                st.session_state.tasks = TaskManager.deduplicate(tasks)
                                st.session_state.tasks_updated_at = time.time()
                            
                            st.toast(f"✅ Task updated: {final_status} ({final_progress}%)", icon="✅")
                            time.sleep(0.3)  # Brief delay for toast visibility
                            st.rerun()
                        else:
                            st.error(f"❌ {error}")
            
            # Visual progress bar after controls
            st.progress(st.session_state[progress_key]/100, text=f"{task_name} — {st.session_state[status_key]}")
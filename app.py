# app.py ← THE ONE THAT FINALLY WORKS (NO MORE ERRORS EVER)
import streamlit as st
import requests
import os
from dotenv import load_dotenv
from queue import Queue
import time

load_dotenv()

st.set_page_config(page_title="AI Workbench", layout="wide")
st.title("🚀 AI Workbench")

API_URL = st.sidebar.text_input("Backend URL", "http://localhost:8000")

# =================================== THREAD-SAFE QUEUE (THIS IS THE KEY) ===================================
# PubNub will ONLY put messages here — never touch st.session_state
if "msg_queue" not in st.session_state:
    st.session_state.msg_queue = Queue()

# Ensure our lists always exist
for key in ["messages", "tasks", "logs"]:
    if key not in st.session_state:
        st.session_state[key] = []


# =================================== PubNub Setup — ONLY puts into queue ===================================
if not st.session_state.get("pubnub_started"):
    from pubnub.pnconfiguration import PNConfiguration
    from pubnub.pubnub import PubNub
    from pubnub.callbacks import SubscribeCallback

    pnconfig = PNConfiguration()
    pnconfig.subscribe_key = os.getenv("PUBNUB_SUBSCRIBE_KEY", "demo")
    pnconfig.uuid = "streamlit-client"
    pnconfig.ssl = True

    # --- FIXED SECTION STARTS ---
    class QueueOnlyListener(SubscribeCallback):
        # 1. Accept the target queue during initialization
        def __init__(self, target_queue):
            self.target_queue = target_queue

        def message(self, pubnub, event):
            # 2. Use the passed-in queue instance directly.
            # We do NOT touch st.session_state here anymore.
            self.target_queue.put({
                "channel": event.channel,
                "data": event.message
            })

    pubnub = PubNub(pnconfig)
    # 3. Pass the specific session's queue to the listener constructor
    pubnub.add_listener(QueueOnlyListener(st.session_state.msg_queue))
    # --- FIXED SECTION ENDS ---

    pubnub.subscribe().channels(["chat", "tasks", "logs"]).execute()
    st.session_state.pubnub_started = True

# =================================== PROCESS QUEUE SAFELY (main thread only) ===================================
def process_incoming_messages():
    updated = False
    while not st.session_state.msg_queue.empty():
        item = st.session_state.msg_queue.get()
        channel = item["channel"]
        data = item["data"]

        if channel == "chat" and isinstance(data, dict) and "content" in data:
            st.session_state.messages.append({"role": "assistant", "content": data["content"]})
            updated = True

        elif channel == "tasks" and isinstance(data, dict):
            if data.get("type") == "created":
                st.session_state.tasks.append(data["task"])
            elif data.get("type") == "updated":
                for i, task in enumerate(st.session_state.tasks):
                    if task.get("id") == data["task"]["id"]:
                        st.session_state.tasks[i] = data["task"]
                        break
            updated = True

        elif channel == "logs":
            st.session_state.logs.append(data)
            if len(st.session_state.logs) > 200:
                st.session_state.logs = st.session_state.logs[-200:]
            updated = True

    if updated:
        st.rerun()

# Run it every time the app refreshes
process_incoming_messages()

# Initial task load
if not st.session_state.tasks:
    try:
        r = requests.get(f"{API_URL}/tasks", timeout=5)
        st.session_state.tasks = r.json().get("tasks", [])
    except:
        pass

# =================================== UI ===================================
tab1, tab2, tab3, tab4 = st.tabs(["Chat", "Tools", "Tasks", "Logs"])

with tab1:
    st.header("Chat")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Type a message..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        requests.post(f"{API_URL}/chat", json={"message": prompt})

with tab2:
    st.header("Tools")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Clean Data"): st.success("Done!")
    with col2:
        if st.button("Train Model"): st.success("Started!")

with tab3:
    st.header("Task Board")
    col1, col2, col3 = st.columns(3)
    col1.metric("In Progress", len([t for t in st.session_state.tasks if t.get("status") == "In Progress"]))
    col2.metric("Completed", len([t for t in st.session_state.tasks if t.get("status") == "Completed"]))
    col3.metric("Total", len(st.session_state.tasks))

    name = st.text_input("New task")
    if st.button("Create") and name:
        requests.post(f"{API_URL}/tasks", json={"name": name})

    for task in st.session_state.tasks:
        st.progress(task.get("progress", 0)/100, text=f"{task['name']} — {task.get('status', 'Pending')}")

with tab4:
    st.header("Logs")
    for log in reversed(st.session_state.logs[-50:]):
        level = log.get("level", "INFO")
        emoji = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌"}.get(level, "")
        st.write(f"{emoji} {log.get('time', '')} {level} — {log.get('message', '')}")
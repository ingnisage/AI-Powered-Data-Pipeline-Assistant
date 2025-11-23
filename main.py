# main.py
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
import os
from dotenv import load_dotenv
from typing import Optional, Dict, Any
import uvicorn
from datetime import datetime

load_dotenv()

app = FastAPI(title="AI Workbench Backend")

# ==================== OpenAI ====================
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None

# ==================== PubNub Real-time ====================
pnconfig = PNConfiguration()
pnconfig.publish_key = os.getenv("PUBNUB_PUBLISH_KEY", "demo")
pnconfig.subscribe_key = os.getenv("PUBNUB_SUBSCRIBE_KEY", "demo")
pnconfig.uuid = "ai-workbench-server"
pnconfig.ssl = True

pubnub = PubNub(pnconfig)

def publish(channel: str, data: Dict[Any, Any]):
    try:
        pubnub.publish().channel(channel).message(data).pn_async(lambda r, s: None)
    except:
        pass  # silent fail in dev

# In-memory fake data (no database!)
tasks = [
    {"id": 1, "name": "Data Preprocessing", "status": "Completed", "progress": 100},
    {"id": 2, "name": "Model Training", "status": "In Progress", "progress": 65},
    {"id": 3, "name": "Model Evaluation", "status": "Pending", "progress": 0},
]

logs = [
    {"time": "2025-04-05 10:00", "level": "INFO", "message": "System started"},
    {"time": "2025-04-05 10:01", "level": "INFO", "message": "Connected to OpenAI"},
]

# ==================== Models ====================
class ChatMessage(BaseModel):
    message: str

class NewTask(BaseModel):
    name: str

# ==================== Routes ====================
@app.get("/")
def home():
    return {"message": "AI Workbench Backend Running 🚀"}

@app.post("/chat")
async def chat(msg: ChatMessage):
    user_msg = msg.message

    if openai_client:
        try:
            resp = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": user_msg}],
                temperature=0.7
            )
            answer = resp.choices[0].message.content
        except Exception as e:
            answer = f"OpenAI error: {e}"
    else:
        answer = f"[Mock] You said: {user_msg}"

    # Real-time broadcast to all frontends
    publish("chat", {"role": "assistant", "content": answer})
    publish("logs", {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "level": "INFO", "message": f"Chat: {user_msg[:30]}..."})

    return {"answer": answer}

@app.get("/tasks")
def get_tasks():
    return {"tasks": tasks}

@app.post("/tasks")
def create_task(task: NewTask):
    new_task = {
        "id": len(tasks) + 1,
        "name": task.name,
        "status": "In Progress",
        "progress": 25
    }
    tasks.append(new_task)
    publish("tasks", {"type": "created", "task": new_task})
    publish("logs", {"time": datetime.now().strftime("%H:%M:%S"), "level": "INFO", "message": f"Task created: {task.name}"})
    return {"task": new_task}

@app.get("/logs")
def get_logs():
    return {"logs": logs[-50:]}  # last 50 logs

# Simulate task progress (fun demo)
import asyncio
async def simulate_progress():
    while True:
        await asyncio.sleep(8)
        for t in tasks:
            if t["status"] == "In Progress" and t["progress"] < 100:
                t["progress"] += 15
                if t["progress"] >= 100:
                    t["progress"] = 100
                    t["status"] = "Completed"
                publish("tasks", {"type": "updated", "task": t})
        await asyncio.sleep(8)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(simulate_progress())

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
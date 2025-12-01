# main.py
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
import os
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
import uvicorn
from datetime import datetime
import json
import asyncio

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

# ==================== System Prompts & Tools ====================
SYSTEM_PROMPTS = {
    "data_engineer": """You are a senior data engineer with 10+ years of experience. 
Your expertise includes:
- Data pipeline design and optimization
- ETL/ELT processes
- Database architecture (SQL, NoSQL)
- Big Data technologies (Spark, Hadoop)
- Data quality and governance
- Cloud data platforms (AWS, GCP, Azure)

Always provide practical, production-ready advice. Focus on scalability, maintainability, and best practices.""",

    "ml_engineer": """You are a senior machine learning engineer specializing in:
- Model development and deployment
- MLOps and pipeline automation
- Feature engineering
- Model monitoring and evaluation
- Distributed training
- Explainable AI

Provide code examples where relevant and discuss trade-offs between different approaches.""",

    "analyst": """You are a senior data analyst expert in:
- SQL query optimization
- Data visualization and storytelling
- Statistical analysis
- A/B testing design
- Business intelligence
- KPI definition and tracking

Focus on actionable insights and business impact.""",

    "general": """You are a helpful AI assistant specialized in data and AI workflows.
Provide clear, concise, and practical advice. Ask clarifying questions when needed."""
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_data_source",
            "description": "Query a data source to get sample data or schema information",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_type": {
                        "type": "string",
                        "enum": ["database", "api", "file", "stream"],
                        "description": "Type of data source to query"
                    },
                    "query": {
                        "type": "string",
                        "description": "SQL query, API endpoint, or file path"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of records to return",
                        "default": 10
                    }
                },
                "required": ["source_type", "query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_data_quality",
            "description": "Analyze data quality metrics for a dataset",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "Identifier for the dataset"
                    },
                    "metrics": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["completeness", "accuracy", "consistency", "timeliness", "uniqueness"]
                        },
                        "description": "Data quality metrics to analyze"
                    }
                },
                "required": ["dataset_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_sql_query",
            "description": "Generate optimized SQL query for data analysis",
            "parameters": {
                "type": "object",
                "properties": {
                    "requirement": {
                        "type": "string",
                        "description": "Business requirement or analysis goal"
                    },
                    "database_type": {
                        "type": "string",
                        "enum": ["postgresql", "mysql", "bigquery", "snowflake", "redshift"],
                        "description": "Type of database"
                    },
                    "complexity": {
                        "type": "string",
                        "enum": ["simple", "intermediate", "complex"],
                        "description": "Complexity level of the query"
                    }
                },
                "required": ["requirement", "database_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_data_pipeline",
            "description": "Schedule or trigger a data pipeline execution",
            "parameters": {
                "type": "object",
                "properties": {
                    "pipeline_id": {
                        "type": "string",
                        "description": "Identifier of the pipeline to schedule"
                    },
                    "schedule_type": {
                        "type": "string",
                        "enum": ["immediate", "daily", "hourly", "weekly", "monthly"],
                        "description": "When to execute the pipeline"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Additional parameters for the pipeline"
                    }
                },
                "required": ["pipeline_id"]
            }
        }
    }
]

# ==================== Tool Implementation ====================
class ToolExecutor:
    @staticmethod
    def execute_tool_call(tool_name: str, arguments: dict) -> dict:
        """Execute tool calls and return results"""
        try:
            if tool_name == "query_data_source":
                return ToolExecutor._query_data_source(**arguments)
            elif tool_name == "analyze_data_quality":
                return ToolExecutor._analyze_data_quality(**arguments)
            elif tool_name == "generate_sql_query":
                return ToolExecutor._generate_sql_query(**arguments)
            elif tool_name == "schedule_data_pipeline":
                return ToolExecutor._schedule_data_pipeline(**arguments)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}

    @staticmethod
    def _query_data_source(source_type: str, query: str, limit: int = 10) -> dict:
        # Mock implementation - in real scenario, connect to actual data sources
        return {
            "source_type": source_type,
            "query": query,
            "limit": limit,
            "sample_data": [
                {"id": i, "value": f"sample_{i}", "timestamp": datetime.now().isoformat()}
                for i in range(min(limit, 5))
            ],
            "schema": {"columns": ["id", "value", "timestamp"], "types": ["int", "str", "datetime"]},
            "row_count": 1000,
            "execution_time": "0.45s"
        }

    @staticmethod
    def _analyze_data_quality(dataset_id: str, metrics: List[str] = None) -> dict:
        if metrics is None:
            metrics = ["completeness", "accuracy", "consistency"]
        
        # Mock quality analysis
        return {
            "dataset_id": dataset_id,
            "metrics_analyzed": metrics,
            "results": {
                "completeness": 0.95,
                "accuracy": 0.88,
                "consistency": 0.92,
                "timeliness": 0.97,
                "uniqueness": 0.99
            },
            "issues_found": [
                "5% missing values in 'user_age' column",
                "Inconsistent date formats in 'created_at'"
            ],
            "recommendations": [
                "Implement data validation rules",
                "Add missing value imputation"
            ]
        }

    @staticmethod
    def _generate_sql_query(requirement: str, database_type: str, complexity: str = "intermediate") -> dict:
        # Mock SQL generation
        sample_queries = {
            "simple": f"SELECT * FROM data_table WHERE condition = 'value' LIMIT 100",
            "intermediate": f"""WITH ranked_data AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC) as rn
    FROM user_activities
)
SELECT user_id, activity_type, COUNT(*) as activity_count
FROM ranked_data 
WHERE rn = 1
GROUP BY user_id, activity_type
HAVING COUNT(*) > 5
ORDER BY activity_count DESC;""",
            "complex": f"""WITH user_metrics AS (
    SELECT 
        user_id,
        COUNT(DISTINCT session_id) as total_sessions,
        AVG(session_duration) as avg_session_duration,
        MAX(created_at) as last_activity
    FROM user_sessions 
    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY user_id
),
purchase_metrics AS (
    SELECT 
        user_id,
        COUNT(*) as total_purchases,
        SUM(amount) as total_spent
    FROM purchases
    WHERE status = 'completed'
    GROUP BY user_id
)
SELECT 
    u.user_id,
    u.total_sessions,
    u.avg_session_duration,
    COALESCE(p.total_purchases, 0) as total_purchases,
    COALESCE(p.total_spent, 0) as total_spent,
    CASE 
        WHEN p.total_spent > 1000 THEN 'VIP'
        WHEN p.total_spent > 100 THEN 'Premium' 
        ELSE 'Standard'
    END as user_tier
FROM user_metrics u
LEFT JOIN purchase_metrics p ON u.user_id = p.user_id
WHERE u.last_activity >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY p.total_spent DESC NULLS LAST;"""
        }
        
        return {
            "requirement": requirement,
            "database_type": database_type,
            "complexity": complexity,
            "generated_query": sample_queries.get(complexity, sample_queries["intermediate"]),
            "optimization_tips": [
                "Add appropriate indexes on filtered columns",
                "Consider partitioning by date if dealing with large datasets",
                "Use EXPLAIN ANALYZE to check query performance"
            ]
        }

    @staticmethod
    def _schedule_data_pipeline(pipeline_id: str, schedule_type: str = "immediate", parameters: dict = None) -> dict:
        # Mock pipeline scheduling
        return {
            "pipeline_id": pipeline_id,
            "schedule_type": schedule_type,
            "scheduled_time": datetime.now().isoformat(),
            "execution_id": f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "status": "scheduled",
            "estimated_duration": "15 minutes",
            "parameters": parameters or {}
        }

# ==================== In-memory data ====================
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
    system_prompt: str = "general"  # default system prompt
    use_tools: bool = False

class NewTask(BaseModel):
    name: str

# ==================== Routes ====================
@app.get("/")
def home():
    return {"message": "AI Workbench Backend Running 🚀"}

@app.get("/system-prompts")
def get_system_prompts():
    """Get available system prompts"""
    return {"prompts": list(SYSTEM_PROMPTS.keys())}

@app.get("/tools")
def get_available_tools():
    """Get available tools"""
    return {"tools": [tool["function"]["name"] for tool in TOOLS]}

@app.post("/chat")
async def chat(msg: ChatMessage):
    user_msg = msg.message
    system_prompt_key = msg.system_prompt
    use_tools = msg.use_tools

    # Get selected system prompt
    system_prompt_content = SYSTEM_PROMPTS.get(system_prompt_key, SYSTEM_PROMPTS["general"])

    if openai_client:
        try:
            # Prepare messages with system prompt
            messages = [
                {"role": "system", "content": system_prompt_content},
                {"role": "user", "content": user_msg}
            ]

            # Prepare API call parameters
            api_params = {
                "model": "gpt-4o",
                "messages": messages,
                "temperature": 0.7
            }

            # Add tools if requested
            if use_tools:
                api_params["tools"] = TOOLS
                api_params["tool_choice"] = "auto"

            # Make API call
            response = openai_client.chat.completions.create(**api_params)
            
            # Process response
            response_message = response.choices[0].message
            answer = response_message.content

            # Handle tool calls
            tool_results = []
            if response_message.tool_calls:
                answer = "I'm executing the requested tools...\n\n"
                
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # Execute tool
                    tool_result = ToolExecutor.execute_tool_call(function_name, function_args)
                    tool_results.append({
                        "tool_name": function_name,
                        "arguments": function_args,
                        "result": tool_result
                    })
                    
                    # Add tool call to answer
                    answer += f"🔧 **{function_name}**: {json.dumps(function_args, indent=2)}\n"
                    answer += f"📊 **Result**: {json.dumps(tool_result, indent=2)}\n\n"

                # Optional: Send tool results back to OpenAI for further processing
                # This would be another API call in a real implementation

            # Real-time broadcast
            publish("chat", {"role": "assistant", "content": answer})
            
            # Log tool usage
            if tool_results:
                publish("logs", {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                    "level": "INFO", 
                    "message": f"Tools executed: {[tr['tool_name'] for tr in tool_results]}"
                })
            else:
                publish("logs", {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                    "level": "INFO", 
                    "message": f"Chat: {user_msg[:30]}..."
                })

            return {
                "answer": answer,
                "system_prompt": system_prompt_key,
                "tools_used": [tr["tool_name"] for tr in tool_results],
                "tool_results": tool_results
            }

        except Exception as e:
            error_msg = f"OpenAI error: {e}"
            publish("chat", {"role": "assistant", "content": error_msg})
            return {"answer": error_msg, "error": str(e)}
    else:
        # Mock response
        answer = f"[Mock - {system_prompt_key}] You said: {user_msg}"
        publish("chat", {"role": "assistant", "content": answer})
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
    publish("logs", {
        "time": datetime.now().strftime("%H:%M:%S"), 
        "level": "INFO", 
        "message": f"Task created: {task.name}"
    })
    return {"task": new_task}

@app.get("/logs")
def get_logs():
    return {"logs": logs[-50:]}

# ==================== Background Tasks ====================
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
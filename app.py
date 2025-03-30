from flask import Flask, render_template, request, jsonify
from agent_core import AutonomousAgent, AgentConfig
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# 搜索引擎配置
SEARCH_APIS = {
    "google": {
        "api_key": os.getenv("GOOGLE_API_KEY"),
        "endpoint": "https://serpapi.com/search"
    },
    "bing": {
        "api_key": os.getenv("BING_API_KEY"),
        "endpoint": "https://api.bing.microsoft.com/v7.0/search"
    },
    "duckduckgo": {
        "api_key": os.getenv("DDG_API_KEY"),
        "endpoint": "https://api.duckduckgo.com/"
    }
}

# 初始化智能体
agent_config = AgentConfig(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    search_apis=SEARCH_APIS,
    enable_meta_search=True,
    cache_search_results=True,
    max_search_results=7
)

agent = AutonomousAgent(agent_config)

@app.before_request
async def before_first_request():
    if not hasattr(app, 'agent_initialized'):
        await agent.initialize()
        app.agent_initialized = True

@app.teardown_appcontext
async def cleanup(exception=None):
    await agent.close()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
async def chat():
    """处理聊天消息"""
    data = request.json
    message = data.get("message", "").strip()
    
    if not message:
        return jsonify({"error": "Empty message"}), 400
    
    # 处理指令
    if message.startswith("/goal "):
        response = agent.set_goal(message[6:])
        return jsonify({"response": response, "type": "text"})
    elif message.startswith("/execute "):
        response = await agent.execute_task(message[9:])
        return jsonify({"response": response, "type": "text"})
    elif message.startswith("/plan "):
        tasks = agent.plan_tasks(message[6:])
        return jsonify({
            "response": "任务计划已生成",
            "type": "plan",
            "tasks": tasks
        })
    elif message == "/reflect":
        response = agent.reflect()
        return jsonify({"response": response, "type": "text"})
    elif message == "/status":
        status = agent.get_status()
        return jsonify({"response": status, "type": "status"})
    else:
        response = agent._call_llm(message)
        return jsonify({"response": response, "type": "text"})

@app.route("/api/memory", methods=["GET"])
async def get_memory():
    """获取记忆数据"""
    return jsonify({
        "memory": agent.memory[-10:],
        "goals": agent.goals,
        "learning": agent.learning_data[-5:]
    })

@app.route("/api/search/stats", methods=["GET"])
async def search_stats():
    """获取搜索统计"""
    if agent.search_engine:
        stats = agent.search_engine.get_sources_statistics()
        return jsonify(stats)
    return jsonify({"error": "Search not enabled"}), 400

@app.route("/api/clear", methods=["POST"])
async def clear_data():
    """清除数据"""
    agent.memory = []
    agent.goals = []
    agent.learning_data = []
    return jsonify({"status": "success"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
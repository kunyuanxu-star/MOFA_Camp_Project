from flask import Flask, render_template, request, jsonify
from agent_core import AutonomousAgentCore
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
    }
}

# 初始化智能体
agent = AutonomousAgentCore(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    search_apis=SEARCH_APIS
)

@app.before_first_request
async def initialize():
    await agent.initialize()

@app.teardown_appcontext
async def cleanup(exception=None):
    await agent.close()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
async def chat():
    user_input = request.json.get("message", "").strip()
    
    if not user_input:
        return jsonify({"response": "请输入有效消息", "type": "error"})
    
    if user_input.startswith("/goal "):
        response = agent.set_goal(user_input[6:])
        return jsonify({"response": response, "type": "text"})
    elif user_input.startswith("/execute "):
        response = await agent.execute_task(user_input[9:])
        return jsonify({"response": response, "type": "text"})
    elif user_input.startswith("/plan "):
        tasks = agent.plan_tasks(user_input[6:])
        return jsonify({
            "response": f"已生成执行计划",
            "tasks": tasks,
            "type": "plan"
        })
    elif user_input == "/reflect":
        response = agent.reflect_and_learn()
        return jsonify({"response": response, "type": "text"})
    else:
        response = agent._call_llm(user_input)
        return jsonify({"response": response, "type": "text"})

@app.route("/memory", methods=["GET"])
def get_memory():
    return jsonify({
        "memory": agent.memory,
        "goals": agent.goals,
        "learning": agent.learning_data[-5:] if agent.learning_data else []
    })

@app.route("/clear", methods=["POST"])
def clear_memory():
    agent.memory = []
    agent.goals = []
    agent.learning_data = []
    return jsonify({"status": "success", "message": "记忆已清空"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
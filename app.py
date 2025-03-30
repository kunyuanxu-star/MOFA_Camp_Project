from flask import Flask, render_template, request, jsonify
from agent_core import AutonomousAgentCore
import os
from datetime import datetime

app = Flask(__name__)

# 初始化自主智能体
agent = AutonomousAgentCore(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    search_api_key=os.getenv("SERPAPI_KEY")
)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")
    
    # 判断是否是目标设置指令
    if user_input.startswith("/goal "):
        goal = user_input[6:]
        response = agent.set_goal(goal)
    elif user_input.startswith("/execute "):
        task = user_input[9:]
        response = agent.execute_task(task)
    elif user_input == "/reflect":
        response = agent.reflect_and_learn()
    elif user_input.startswith("/plan "):
        objective = user_input[6:]
        tasks = agent.plan_tasks(objective)
        return jsonify({"response": "计划已生成", "tasks": tasks})
    else:
        # 普通聊天处理
        response = agent._call_llm(user_input)
    
    return jsonify({"response": response})

@app.route("/plan", methods=["POST"])
def plan():
    objective = request.json.get("objective")
    tasks = agent.plan_tasks(objective)
    return jsonify({"tasks": tasks})

@app.route("/memory", methods=["GET"])
def get_memory():
    return jsonify({"memory": agent.memory})

if __name__ == "__main__":
    app.run(debug=True)
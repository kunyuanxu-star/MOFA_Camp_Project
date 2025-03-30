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
    """主页面路由"""
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    """
    处理聊天消息
    支持以下指令:
    - /goal [目标]: 设置新目标
    - /execute [任务]: 执行任务
    - /plan [目标]: 生成任务计划
    - /reflect: 执行自我反思
    - 普通消息: 常规对话
    """
    user_input = request.json.get("message", "").strip()
    
    if not user_input:
        return jsonify({"response": "请输入有效消息"})
    
    # 处理指令
    if user_input.startswith("/goal "):
        goal = user_input[6:]
        response = agent.set_goal(goal)
    elif user_input.startswith("/execute "):
        task = user_input[9:]
        response = agent.execute_task(task)
    elif user_input.startswith("/plan "):
        objective = user_input[6:]
        tasks = agent.plan_tasks(objective)
        return jsonify({
            "response": f"已为'{objective}'生成计划",
            "tasks": tasks,
            "type": "plan"
        })
    elif user_input == "/reflect":
        response = agent.reflect_and_learn()
    else:
        # 普通聊天处理
        response = agent._call_llm(user_input)
    
    return jsonify({"response": response, "type": "text"})

@app.route("/memory", methods=["GET"])
def get_memory():
    """获取智能体记忆"""
    return jsonify({
        "memory": agent.memory,
        "goals": agent.goals,
        "learning_data": agent.learning_data
    })

@app.route("/clear", methods=["POST"])
def clear_data():
    """清除智能体数据"""
    agent.memory = []
    agent.goals = []
    agent.learning_data = []
    return jsonify({"status": "success", "message": "已重置智能体记忆"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
from flask import Flask, render_template, request, jsonify
from agent_core import AutonomousAgent, AgentConfig
import os
import asyncio
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__, static_folder='static')

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

# 深网配置
DEEPWEB_CONFIG = {
    "enable": True,
    "tor_proxy": os.getenv("TOR_PROXY", "socks5://localhost:9050"),
    "i2p_proxy": os.getenv("I2P_PROXY", "http://localhost:4444"),
    "warning": "深网内容需要Tor/I2P浏览器访问，请遵守法律法规"
}

# 初始化智能体
agent_config = AgentConfig(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    search_apis=SEARCH_APIS,
    deepweb_config=DEEPWEB_CONFIG,
    default_search_mode=SearchMode.MIXED,
    max_surface_results=10,
    max_deepweb_results=5
)

agent = AutonomousAgent(agent_config)

@app.before_request
async def initialize_agent():
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
    
    try:
        # 处理指令
        if message.startswith("/goal "):
            response = agent.set_goal(message[6:])
            return jsonify({"response": response, "type": "text"})
        
        elif message.startswith("/execute "):
            response = await agent.execute_task(message[9:])
            return jsonify({"response": response, "type": "text"})
        
        elif message.startswith("/search "):
            query = message[7:]
            results = await agent._perform_meta_search(query, "surface")
            return jsonify({
                "response": await agent._format_search_response(results),
                "type": "search_results",
                "results": results
            })
        
        elif message.startswith("/deepsearch "):
            query = message[11:]
            results = await agent._perform_deep_search(query)
            return jsonify({
                "response": await agent._format_search_response(results),
                "type": "search_results",
                "results": results
            })
        
        elif message == "/reflect":
            response = agent.reflect()
            return jsonify({"response": response, "type": "text"})
        
        elif message == "/capabilities":
            capabilities = await agent.get_capabilities()
            return jsonify({
                "response": "智能体能力信息",
                "type": "capabilities",
                "data": capabilities
            })
        
        elif message.startswith("/clear "):
            memory_type = message[7:]
            response = await agent.clear_memory(memory_type)
            return jsonify({"response": response, "type": "text"})
        
        else:
            response = agent._call_llm(message)
            return jsonify({"response": response, "type": "text"})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/memory", methods=["GET"])
async def get_memory():
    """获取记忆内容"""
    try:
        return jsonify({
            "goals": agent.goals,
            "memory": agent.memory[-20:],
            "learning": agent.learning_data[-10:]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/status", methods=["GET"])
async def get_status():
    """获取系统状态"""
    try:
        return jsonify({
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "search_engines": list(SEARCH_APIS.keys()),
            "deepweb_enabled": DEEPWEB_CONFIG["enable"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
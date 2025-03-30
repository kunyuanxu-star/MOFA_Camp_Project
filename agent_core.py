import json
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime
import os
import openai
import asyncio
from dataclasses import dataclass
from enum import Enum, auto

class SearchMode(Enum):
    SURFACE = auto()  # 仅明网搜索
    DEEP = auto()     # 仅深网搜索
    MIXED = auto()    # 混合搜索

@dataclass
class AgentConfig:
    openai_api_key: str
    search_apis: Optional[Dict] = None
    deepweb_config: Optional[Dict] = None
    default_search_mode: SearchMode = SearchMode.MIXED
    max_surface_results: int = 10
    max_deepweb_results: int = 5
    enable_learning: bool = True
    max_memory_size: int = 1000

class AutonomousAgent:
    def __init__(self, config: AgentConfig):
        """
        自主智能体核心(支持深网搜索)
        
        参数:
            config: 智能体配置
        """
        self.config = config
        openai.api_key = config.openai_api_key
        self.memory = []
        self.goals = []
        self.learning_data = []
        self.current_task = None
        self.search_engine = None
        self.tools = self._initialize_base_tools()
        
    async def initialize(self):
        """初始化智能体"""
        if self.config.search_apis:
            from search_tools import MetaSearchEngine
            self.search_engine = MetaSearchEngine(
                self.search_apis,
                deepweb_config=self.config.deepweb_config
            )
            await self.search_engine.initialize()
            self._initialize_search_tools()

    async def close(self):
        """清理资源"""
        if self.search_engine:
            await self.search_engine.close()

    def _initialize_base_tools(self) -> Dict[str, Callable]:
        """初始化基础工具集"""
        return {
            'take_notes': self._take_notes,
            'set_reminder': self._set_reminder,
            'plan_tasks': self.plan_tasks,
            'reflect': self.reflect,
            'get_time': self._get_current_time
        }

    def _initialize_search_tools(self):
        """初始化搜索工具"""
        self.tools.update({
            'meta_search': self._perform_meta_search,
            'deep_search': self._perform_deep_search,
            'surface_search': self._perform_surface_search
        })

    def _trim_memory(self):
        """修剪记忆以避免过大"""
        if len(self.memory) > self.config.max_memory_size:
            self.memory = self.memory[-self.config.max_memory_size:]

    async def _perform_meta_search(self, query: str, mode: str = None) -> Dict:
        """
        执行元搜索
        参数:
            mode: surface/deep/mixed
        """
        if not self.search_engine:
            return {"error": "Search engine not initialized"}
        
        mode = mode or self.config.default_search_mode.name.lower()
        return await self.search_engine.meta_search(query, mode)

    async def _perform_deep_search(self, query: str) -> Dict:
        """专用深网搜索"""
        return await self._perform_meta_search(query, "deep")

    async def _perform_surface_search(self, query: str) -> Dict:
        """专用明网搜索"""
        return await self._perform_meta_search(query, "surface")

    async def _format_search_response(self, results: Dict) -> str:
        """格式化搜索结果响应"""
        if "error" in results:
            return results["error"]
        
        if not any(results.values()):
            return "🔍 没有找到相关搜索结果"
        
        return self.search_engine.format_results(results)

    def _get_current_time(self) -> str:
        """获取当前时间"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _take_notes(self, content: str) -> str:
        """记录笔记"""
        note = {
            "content": content,
            "timestamp": self._get_current_time(),
            "type": "note"
        }
        self.memory.append(note)
        self._trim_memory()
        return f"📝 已记录笔记: {content}"

    def _set_reminder(self, time: str, task: str) -> str:
        """设置提醒"""
        reminder = {
            "time": time,
            "task": task,
            "timestamp": self._get_current_time(),
            "type": "reminder"
        }
        self.memory.append(reminder)
        self._trim_memory()
        return f"⏰ 已设置提醒: 在 {time} 执行 {task}"

    def set_goal(self, goal: str) -> str:
        """设置目标"""
        goal_entry = {
            "description": goal,
            "created": self._get_current_time(),
            "status": "active"
        }
        self.goals.append(goal_entry)
        return f"🎯 新目标已设定: {goal}"

    def plan_tasks(self, objective: str) -> List[Dict]:
        """制定任务计划"""
        prompt = f"""你是一个任务规划AI。请将以下目标分解为具体可执行步骤:

目标: {objective}

要求:
1. 分解为3-5个清晰的步骤
2. 每个步骤应有明确的描述和预期结果
3. 考虑步骤之间的依赖关系
4. 推荐适合的工具
5. 使用以下JSON格式返回:

{{
    "tasks": [
        {{
            "step": 1,
            "description": "任务描述",
            "expected_outcome": "预期结果",
            "dependencies": [],
            "tools_needed": []
        }}
    ]
}}"""
        
        response = self._call_llm(prompt, max_tokens=600)
        try:
            return json.loads(response).get("tasks", [])
        except json.JSONDecodeError as e:
            print(f"解析任务计划出错: {str(e)}")
            return []

    async def execute_task(self, task: str) -> str:
        """执行任务(支持深网搜索)"""
        self.current_task = task
        
        # 判断是否需要深网搜索
        use_deepweb = any(keyword in task.lower() for keyword in [
            "深网", "dark web", "tor", "i2p", "暗网", "onion", ".i2p"
        ])
        
        prompt = f"""你是一个AI执行者。请执行以下任务:

任务: {task}

可用工具: {list(self.tools.keys())}
{"注意: 此任务可能需要深网搜索" if use_deepweb else ""}

思考步骤:
1. 分析任务需求和上下文
2. 决定是否需要使用工具
3. 选择最适合的工具和参数
4. 执行操作并返回结果

请用以下JSON格式返回你的执行计划:
{{
    "thought_process": "你的思考过程",
    "tool_used": "使用的工具名称",
    "arguments": {{
        "query": "搜索查询(如适用)",
        "mode": "搜索模式(surface/deep/mixed)",
        "other_params": "其他参数"
    }},
    "result": "执行结果"
}}"""
        
        response = self._call_llm(prompt, max_tokens=800)
        try:
            execution = json.loads(response)
            
            # 处理工具调用
            if execution.get("tool_used"):
                tool_func = self.tools.get(execution["tool_used"])
                if tool_func:
                    args = execution.get("arguments", {})
                    if asyncio.iscoroutinefunction(tool_func):
                        raw_results = await tool_func(**args)
                        execution["result"] = await self._format_search_response(raw_results)
                    else:
                        execution["result"] = tool_func(**args)
            
            # 记录执行历史
            if self.config.enable_learning:
                self.learning_data.append({
                    "task": task,
                    "execution": execution,
                    "timestamp": self._get_current_time(),
                    "used_deepweb": use_deepweb
                })
                self._trim_memory()
            
            return execution.get("result", "✅ 任务执行完成")
        except Exception as e:
            error_msg = f"❌ 任务执行出错: {str(e)}"
            if self.config.enable_learning:
                self.learning_data.append({
                    "task": task,
                    "error": error_msg,
                    "timestamp": self._get_current_time()
                })
            return error_msg

    def reflect(self) -> str:
        """自我反思和学习"""
        if not self.learning_data:
            return "暂无足够的学习数据"
            
        prompt = f"""你是一个AI学习者。请分析以下执行历史并提取经验:

执行历史(最近3条):
{json.dumps(self.learning_data[-3:], ensure_ascii=False, indent=2)}

要求:
1. 识别成功的模式和策略
2. 分析失败的原因和错误
3. 提出3条具体的改进建议
4. 总结对未来任务的指导原则
5. 使用以下JSON格式返回:

{{
    "success_patterns": ["模式1", "模式2"],
    "common_errors": ["错误1", "错误2"],
    "improvements": ["建议1", "建议2", "建议3"],
    "guidelines": ["原则1", "原则2"]
}}"""
        
        response = self._call_llm(prompt, max_tokens=800)
        try:
            insights = json.loads(response)
            learning_record = {
                "type": "learning_insights",
                "content": insights,
                "timestamp": self._get_current_time()
            }
            self.memory.append(learning_record)
            self._trim_memory()
            
            # 格式化输出
            output = ["🧠 学习总结:"]
            output.append("\n✔️ 成功模式:")
            output.extend(f"- {pattern}" for pattern in insights.get("success_patterns", []))
            output.append("\n❌ 常见错误:")
            output.extend(f"- {error}" for error in insights.get("common_errors", []))
            output.append("\n💡 改进建议:")
            output.extend(f"- {improvement}" for improvement in insights.get("improvements", []))
            
            return "\n".join(output)
        except json.JSONDecodeError:
            return response

    def _call_llm(self, prompt: str, **kwargs) -> str:
        """调用语言模型"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            return response.choices[0].message['content']
        except Exception as e:
            return f"⚠️ 语言模型调用出错: {str(e)}"

    async def get_capabilities(self) -> Dict:
        """获取智能体能力信息"""
        capabilities = {
            "surface_engines": list(self.config.search_apis.keys()) if self.config.search_apis else [],
            "deepweb_enabled": bool(
                self.config.deepweb_config and 
                self.config.deepweb_config.get("enable")
            ),
            "default_search_mode": self.config.default_search_mode.name,
            "max_results": {
                "surface": self.config.max_surface_results,
                "deepweb": self.config.max_deepweb_results
            },
            "memory_stats": {
                "goals": len(self.goals),
                "memory_entries": len(self.memory),
                "learning_records": len(self.learning_data)
            },
            "tools_available": list(self.tools.keys())
        }
        
        if capabilities["deepweb_enabled"]:
            capabilities["deepweb_config"] = {
                "tor_proxy": bool(self.config.deepweb_config.get("tor_proxy")),
                "i2p_proxy": bool(self.config.deepweb_config.get("i2p_proxy"))
            }
        
        return capabilities

    async def clear_memory(self, memory_type: str = "all") -> str:
        """清除指定类型的记忆"""
        if memory_type == "all":
            self.memory = []
            self.learning_data = []
            self.goals = []
            return "所有记忆已清空"
        elif memory_type == "goals":
            self.goals = []
            return "目标已清空"
        elif memory_type == "learning":
            self.learning_data = []
            return "学习记录已清空"
        else:
            return "无效的记忆类型"
import json
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime
import os
import openai
import asyncio
from dataclasses import dataclass

@dataclass
class AgentConfig:
    openai_api_key: str
    search_apis: Optional[Dict] = None
    enable_meta_search: bool = True
    cache_search_results: bool = True
    max_search_results: int = 5

class AutonomousAgent:
    def __init__(self, config: AgentConfig):
        """
        自主智能体核心
        
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
        self.tools = self._initialize_tools()
        
    async def initialize(self):
        """初始化智能体"""
        if self.config.search_apis and self.config.enable_meta_search:
            from search_tools import MetaSearchEngine
            self.search_engine = MetaSearchEngine(
                self.config.search_apis,
                cache_enabled=self.config.cache_search_results
            )
            await self.search_engine.initialize()
            self.tools["meta_search"] = self._perform_meta_search

    async def close(self):
        """清理资源"""
        if self.search_engine:
            await self.search_engine.close()

    def _initialize_tools(self) -> Dict[str, Callable]:
        """初始化工具集"""
        base_tools = {
            'take_notes': self._take_notes,
            'set_reminder': self._set_reminder,
            'plan_tasks': self.plan_tasks,
            'reflect': self.reflect
        }
        return base_tools

    async def _perform_meta_search(self, query: str, num_results: int = None) -> str:
        """执行元搜索"""
        if not self.search_engine:
            return "搜索功能未启用"
            
        num_results = num_results or self.config.max_search_results
        results = await self.search_engine.meta_search(query, num_results)
        return self.search_engine.format_results(results)

    def _take_notes(self, content: str) -> str:
        """记录笔记"""
        note = {
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "type": "note"
        }
        self.memory.append(note)
        return f"📝 已记录笔记: {content}"

    def _set_reminder(self, time: str, task: str) -> str:
        """设置提醒"""
        reminder = {
            "time": time,
            "task": task,
            "timestamp": datetime.now().isoformat(),
            "type": "reminder"
        }
        self.memory.append(reminder)
        return f"⏰ 已设置提醒: 在 {time} 执行 {task}"

    def set_goal(self, goal: str) -> str:
        """设置目标"""
        goal_entry = {
            "description": goal,
            "created": datetime.now().isoformat(),
            "status": "active"
        }
        self.goals.append(goal_entry)
        return f"🎯 新目标已设定: {goal}"

    def plan_tasks(self, objective: str) -> List[Dict]:
        """制定任务计划"""
        prompt = f"""将以下目标分解为具体任务:
目标: {objective}

要求:
1. 分解为3-5个步骤
2. 每个步骤应明确可执行
3. 考虑步骤依赖关系
4. 返回JSON格式

返回格式:
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
        
        response = self._call_llm(prompt, max_tokens=500)
        try:
            return json.loads(response).get("tasks", [])
        except json.JSONDecodeError:
            return []

    async def execute_task(self, task: str) -> str:
        """执行任务"""
        self.current_task = task
        prompt = f"""执行以下任务:
任务: {task}

可用工具: {list(self.tools.keys())}

思考步骤:
1. 分析需求
2. 决定是否使用工具
3. 选择合适工具
4. 执行任务
5. 返回结果

返回格式:
{{
    "thought_process": "思考过程",
    "tool_used": "使用的工具",
    "arguments": "工具参数(JSON)",
    "result": "执行结果"
}}"""
        
        response = self._call_llm(prompt, max_tokens=500)
        try:
            execution = json.loads(response)
            
            # 处理工具调用
            if execution.get("tool_used"):
                tool_func = self.tools.get(execution["tool_used"])
                if tool_func:
                    args = json.loads(execution.get("arguments", "{}"))
                    if asyncio.iscoroutinefunction(tool_func):
                        execution["result"] = await tool_func(**args)
                    else:
                        execution["result"] = tool_func(**args)
            
            # 记录执行历史
            self.learning_data.append({
                "task": task,
                "execution": execution,
                "timestamp": datetime.now().isoformat()
            })
            
            return execution.get("result", "✅ 任务执行完成")
        except Exception as e:
            return f"❌ 任务执行出错: {str(e)}"

    def reflect(self) -> str:
        """自我反思"""
        if not self.learning_data:
            return "暂无足够的学习数据"
            
        prompt = f"""分析以下执行历史并总结:
执行历史: {json.dumps(self.learning_data[-3:], ensure_ascii=False)}

要求:
1. 识别成功模式
2. 找出常见错误
3. 提出3条改进建议
4. 返回JSON格式"""
        
        response = self._call_llm(prompt, max_tokens=400)
        try:
            insights = json.loads(response)
            self.memory.append({
                "type": "learning_insights",
                "content": insights,
                "timestamp": datetime.now().isoformat()
            })
            return "🧠 学习完成，改进建议已记录"
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

    def get_status(self) -> Dict:
        """获取智能体状态"""
        return {
            "goals": self.goals,
            "memory_size": len(self.memory),
            "learning_count": len(self.learning_data),
            "current_task": self.current_task
        }
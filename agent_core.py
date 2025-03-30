import json
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime
import os
import openai
import asyncio

class AutonomousAgentCore:
    def __init__(self, openai_api_key: str, search_apis: Optional[Dict] = None):
        self.openai_api_key = openai_api_key
        openai.api_key = openai_api_key
        self.search_apis = search_apis
        self.memory = []
        self.goals = []
        self.tools = self._initialize_tools()
        self.current_task = None
        self.learning_data = []
        self.search_tool = None
        
    async def initialize(self):
        """异步初始化"""
        if self.search_apis:
            from search_tools import DistributedSearchTool
            self.search_tool = DistributedSearchTool(self.search_apis)
            await self.search_tool.initialize()
            self.tools['distributed_search'] = self._perform_distributed_search

    async def close(self):
        """清理资源"""
        if self.search_tool:
            await self.search_tool.close()

    def _initialize_tools(self) -> Dict[str, Callable]:
        """初始化工具集"""
        tools = {
            'note_taking': self._take_notes,
            'schedule_reminder': self._schedule_reminder,
            'plan_generation': self.plan_tasks
        }
        return tools

    async def _perform_distributed_search(self, query: str, num_results: int = 5) -> str:
        """执行分布式搜索"""
        if not self.search_tool:
            return "搜索功能未初始化"
            
        results = await self.search_tool.distributed_search(query, num_results)
        return self.search_tool.format_results(results)

    def _take_notes(self, content: str) -> str:
        """记录笔记"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        note = f"[{timestamp}] {content}"
        self.memory.append(note)
        return f"📝 已记录笔记: {note}"

    def _schedule_reminder(self, time: str, task: str) -> str:
        """设置提醒"""
        reminder = {
            "time": time,
            "task": task,
            "created": datetime.now().isoformat()
        }
        self.memory.append(reminder)
        return f"⏰ 已设置提醒: 在 {time} 执行 {task}"

    def set_goal(self, goal_description: str) -> str:
        """设置目标"""
        self.goals.append({
            "description": goal_description,
            "created": datetime.now().isoformat(),
            "status": "active"
        })
        return f"🎯 新目标已设定: {goal_description}"

    def plan_tasks(self, objective: str) -> List[Dict]:
        """制定任务计划"""
        prompt = f"""将以下目标分解为具体任务:
目标: {objective}

要求:
1. 分解为3-5个步骤
2. 每个步骤应明确可执行
3. 考虑步骤依赖关系
4. 返回JSON格式

示例格式:
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

    async def execute_task(self, task_description: str) -> str:
        """执行任务"""
        self.current_task = task_description
        prompt = f"""执行以下任务:
任务: {task_description}

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
                tool = self.tools.get(execution["tool_used"])
                if tool:
                    if execution["tool_used"] == "distributed_search":
                        args = json.loads(execution.get("arguments", "{}"))
                        execution["result"] = await tool(args.get("query", ""), args.get("num_results", 3))
                    else:
                        execution["result"] = tool(**json.loads(execution.get("arguments", "{}")))
            
            self.learning_data.append({
                "task": task_description,
                "execution": execution,
                "timestamp": datetime.now().isoformat()
            })
            
            return execution.get("result", "✅ 任务执行完成")
        except Exception as e:
            return f"❌ 任务执行出错: {str(e)}"

    def reflect_and_learn(self) -> str:
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
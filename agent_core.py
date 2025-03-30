import json
from typing import List, Dict, Optional, Callable
from datetime import datetime
import os
import openai

class AutonomousAgentCore:
    def __init__(self, openai_api_key: str, search_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key
        openai.api_key = openai_api_key
        self.search_api_key = search_api_key
        self.memory = []
        self.goals = []
        self.tools = self._initialize_tools()
        self.current_task = None
        self.learning_data = []
        
    def _initialize_tools(self) -> Dict[str, Callable]:
        """初始化智能体可用的工具集"""
        tools = {}
        
        # 搜索工具
        if self.search_api_key:
            from search_tools import SearchTool
            search_tool = SearchTool(self.search_api_key)
            tools['web_search'] = search_tool.google_search
        
        # 添加更多工具...
        tools['note_taking'] = self._take_notes
        tools['schedule_reminder'] = self._schedule_reminder
        tools['plan_generation'] = self.plan_tasks
        
        return tools
    
    def _take_notes(self, content: str) -> str:
        """笔记工具"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        note = f"[{timestamp}] {content}"
        self.memory.append(note)
        return f"已记录笔记: {note}"
    
    def _schedule_reminder(self, time: str, task: str) -> str:
        """提醒工具"""
        reminder = {
            "time": time,
            "task": task,
            "created": datetime.now().isoformat()
        }
        self.memory.append(reminder)
        return f"已设置提醒: 在 {time} 执行 {task}"
    
    def set_goal(self, goal_description: str):
        """设置智能体的长期目标"""
        self.goals.append({
            "description": goal_description,
            "created": datetime.now().isoformat(),
            "status": "active"
        })
        return f"新目标已设定: {goal_description}"
    
    def plan_tasks(self, objective: str) -> List[Dict]:
        """为给定目标制定执行计划"""
        prompt = f"""
        你是一个高级AI规划师。请将以下目标分解为具体的可执行任务:
        目标: {objective}
        
        要求:
        1. 将目标分解为3-5个具体步骤
        2. 每个步骤应该是明确、可执行的动作
        3. 考虑步骤之间的依赖关系
        4. 返回JSON格式的结果
        
        返回格式示例:
        {{
            "tasks": [
                {{
                    "step": 1,
                    "description": "具体任务描述",
                    "expected_outcome": "预期结果",
                    "dependencies": ["依赖的步骤编号"],
                    "tools_needed": ["需要的工具"]
                }}
            ]
        }}
        """
        
        response = self._call_llm(prompt, max_tokens=500)
        try:
            plan = json.loads(response)
            return plan.get("tasks", [])
        except json.JSONDecodeError:
            return []
    
    def execute_task(self, task_description: str) -> str:
        """执行单个任务并返回结果"""
        self.current_task = task_description
        prompt = f"""
        你是一个AI执行者。请执行以下任务:
        任务: {task_description}
        
        你可以使用的工具: {list(self.tools.keys())}
        
        请按照以下步骤思考:
        1. 分析任务需求
        2. 决定是否需要使用工具
        3. 如果需要工具，选择最合适的工具
        4. 执行任务
        5. 返回执行结果
        
        请用以下格式返回:
        {{
            "thought_process": "你的思考过程",
            "tool_used": "使用的工具(如无需工具则留空)",
            "result": "执行结果"
        }}
        """
        
        response = self._call_llm(prompt, max_tokens=500)
        try:
            execution = json.loads(response)
            
            # 记录学习数据
            self.learning_data.append({
                "task": task_description,
                "execution": execution,
                "timestamp": datetime.now().isoformat()
            })
            
            return execution.get("result", "任务执行完成，但未返回明确结果")
        except json.JSONDecodeError:
            return response
    
    def reflect_and_learn(self):
        """从经验中学习并改进未来表现"""
        if not self.learning_data:
            return "暂无足够的学习数据"
            
        prompt = f"""
        你是一个AI学习者。请分析以下执行历史并总结改进建议:
        执行历史: {json.dumps(self.learning_data[-5:], ensure_ascii=False)}
        
        请:
        1. 识别成功的模式
        2. 找出常见错误
        3. 提出3条具体的改进建议
        4. 返回JSON格式的结果
        """
        
        response = self._call_llm(prompt, max_tokens=400)
        try:
            insights = json.loads(response)
            self.memory.append({
                "type": "learning_insights",
                "content": insights,
                "timestamp": datetime.now().isoformat()
            })
            return "学习完成，改进建议已记录"
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
            return f"调用语言模型出错: {str(e)}"
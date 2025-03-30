import requests
from typing import Optional, Dict, List
import json

class SearchTool:
    def __init__(self, api_key: str):
        """
        初始化搜索工具
        
        参数:
            api_key: SerpAPI密钥 (可从 https://serpapi.com/ 获取)
        """
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"
    
    def google_search(self, query: str, num_results: int = 3) -> List[Dict]:
        """
        执行Google搜索
        
        参数:
            query: 搜索查询
            num_results: 返回的结果数量
            
        返回:
            包含搜索结果的列表
        """
        params = {
            "q": query,
            "api_key": self.api_key,
            "num": num_results
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            results = response.json()
            
            # 提取有机搜索结果
            organic_results = results.get("organic_results", [])
            
            # 简化结果结构
            simplified_results = []
            for result in organic_results:
                simplified_results.append({
                    "title": result.get("title"),
                    "link": result.get("link"),
                    "snippet": result.get("snippet")
                })
            
            return simplified_results
            
        except Exception as e:
            print(f"搜索出错: {str(e)}")
            return []
    
    def format_search_results(self, results: List[Dict]) -> str:
        """
        将搜索结果格式化为字符串
        
        参数:
            results: 搜索结果列表
            
        返回:
            格式化后的搜索结果字符串
        """
        if not results:
            return "没有找到相关搜索结果。"
        
        formatted = "搜索结果显示:\n"
        for i, result in enumerate(results, 1):
            formatted += f"{i}. {result['title']}\n"
            formatted += f"   URL: {result['link']}\n"
            formatted += f"   摘要: {result['snippet']}\n\n"
        
        return formatted.strip()
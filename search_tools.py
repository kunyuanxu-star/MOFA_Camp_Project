import asyncio
import aiohttp
from typing import List, Dict, Optional, Tuple
import json
from datetime import datetime

class DistributedSearchTool:
    def __init__(self, search_apis: Dict[str, dict]):
        """
        分布式搜索工具
        
        参数:
            search_apis: {
                "google": {"api_key": "xxx", "endpoint": "url"},
                "bing": {"api_key": "yyy", "endpoint": "url"}
            }
        """
        self.search_apis = search_apis
        self.timeout = 10
        self.session = None

    async def initialize(self):
        """初始化aiohttp会话"""
        self.session = aiohttp.ClientSession()

    async def close(self):
        """关闭aiohttp会话"""
        if self.session:
            await self.session.close()

    async def _async_search(self, engine: str, query: str, num_results: int = 3) -> Tuple[str, List[Dict]]:
        """异步执行单个搜索引擎查询"""
        if not self.session:
            await self.initialize()

        api_config = self.search_apis.get(engine)
        if not api_config:
            return engine, []

        params = {
            "q": query,
            "api_key": api_config["api_key"],
            "num": num_results
        }

        try:
            async with self.session.get(
                api_config["endpoint"],
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                
                if response.status == 200:
                    results = await response.json()
                    return engine, self._process_results(engine, results)
                return engine, []
                
        except Exception as e:
            print(f"{engine}搜索出错: {str(e)}")
            return engine, []

    def _process_results(self, engine: str, results: Dict) -> List[Dict]:
        """处理不同搜索引擎的返回结果"""
        processed = []
        
        if engine == "google":
            items = results.get("organic_results", [])
            for item in items:
                processed.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "source": "Google",
                    "score": self._calculate_score(item)
                })
                
        elif engine == "bing":
            items = results.get("webPages", {}).get("value", [])
            for item in items:
                processed.append({
                    "title": item.get("name", ""),
                    "link": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                    "source": "Bing",
                    "score": self._calculate_score(item)
                })
                
        return processed[:5]

    def _calculate_score(self, item: Dict) -> float:
        """计算搜索结果相关性分数"""
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        return len(title) * 0.6 + len(snippet) * 0.4

    async def distributed_search(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        分布式并行搜索
        
        参数:
            query: 搜索查询
            num_results: 期望的总结果数
            
        返回:
            整合后的搜索结果列表
        """
        tasks = []
        for engine in self.search_apis.keys():
            tasks.append(self._async_search(engine, query, num_results))
        
        results = await asyncio.gather(*tasks)
        
        # 合并和去重结果
        merged_results = []
        seen_links = set()
        
        for engine, items in results:
            for item in items:
                if item["link"] not in seen_links:
                    merged_results.append(item)
                    seen_links.add(item["link"])
        
        # 按分数排序
        merged_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return merged_results[:num_results]

    def format_results(self, results: List[Dict]) -> str:
        """格式化搜索结果"""
        if not results:
            return "没有找到相关搜索结果。"

        formatted = "🔍 分布式搜索结果:\n\n"
        for i, result in enumerate(results, 1):
            formatted += f"{i}. [{result['source']}] {result['title']}\n"
            formatted += f"   🌐 {result['link']}\n"
            formatted += f"   📝 {result['snippet']}\n\n"
        
        return formatted.strip()
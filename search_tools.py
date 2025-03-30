import asyncio
import aiohttp
from typing import List, Dict, Optional, Tuple
import json
from datetime import datetime
import hashlib

class MetaSearchEngine:
    def __init__(self, search_apis: Dict[str, dict], cache_enabled: bool = True):
        """
        元搜索引擎
        
        参数:
            search_apis: 搜索引擎配置字典
            cache_enabled: 是否启用结果缓存
        """
        self.search_apis = search_apis
        self.timeout = 10
        self.session = None
        self.cache_enabled = cache_enabled
        self.result_cache = {}
        
    async def initialize(self):
        """初始化aiohttp会话"""
        self.session = aiohttp.ClientSession()

    async def close(self):
        """关闭aiohttp会话"""
        if self.session:
            await self.session.close()

    def _get_cache_key(self, query: str) -> str:
        """生成缓存键"""
        return hashlib.md5(query.encode('utf-8')).hexdigest()

    async def _fetch_from_engine(self, engine: str, query: str, num_results: int) -> Tuple[str, List[Dict]]:
        """从单个引擎获取结果"""
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
                    return engine, self._normalize_results(engine, results)
                return engine, []
                
        except Exception as e:
            print(f"{engine}搜索出错: {str(e)}")
            return engine, []

    def _normalize_results(self, engine: str, results: Dict) -> List[Dict]:
        """标准化不同引擎的结果格式"""
        normalized = []
        
        if engine == "google":
            for item in results.get("organic_results", []):
                normalized.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "source": "Google",
                    "score": self._calculate_relevance(item)
                })
        elif engine == "bing":
            for item in results.get("webPages", {}).get("value", []):
                normalized.append({
                    "title": item.get("name", ""),
                    "link": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                    "source": "Bing",
                    "score": self._calculate_relevance(item)
                })
        elif engine == "duckduckgo":
            for item in results.get("results", []):
                normalized.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("description", ""),
                    "source": "DuckDuckGo",
                    "score": self._calculate_relevance(item)
                })
                
        return normalized[:5]  # 每个引擎最多返回5条结果

    def _calculate_relevance(self, item: Dict) -> float:
        """计算结果相关性分数"""
        title_len = len(item.get("title", ""))
        snippet_len = len(item.get("snippet", ""))
        return (title_len * 0.6 + snippet_len * 0.4) / 100

    async def meta_search(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        执行元搜索
        
        参数:
            query: 搜索查询
            num_results: 期望返回的结果数量
            
        返回:
            整合、去重和排序后的结果列表
        """
        # 检查缓存
        cache_key = self._get_cache_key(query)
        if self.cache_enabled and cache_key in self.result_cache:
            return self.result_cache[cache_key][:num_results]

        # 并行查询所有引擎
        tasks = [self._fetch_from_engine(engine, query, num_results) 
                for engine in self.search_apis.keys()]
        results = await asyncio.gather(*tasks)
        
        # 合并、去重和排序结果
        all_results = []
        seen_urls = set()
        
        for engine, items in results:
            for item in items:
                url = item["link"]
                if url not in seen_urls:
                    # 增加引擎多样性分数
                    item["score"] += 0.1 * (1 - len(seen_urls)/num_results)
                    all_results.append(item)
                    seen_urls.add(url)
        
        # 按综合分数排序
        all_results.sort(key=lambda x: x["score"], reverse=True)
        
        # 缓存结果
        if self.cache_enabled:
            self.result_cache[cache_key] = all_results
        
        return all_results[:num_results]

    def format_results(self, results: List[Dict], include_source: bool = True) -> str:
        """格式化搜索结果用于显示"""
        if not results:
            return "🔍 没有找到相关搜索结果。"
            
        formatted = ["<div class='meta-search-results'>"]
        formatted.append("<h3>🌐 元搜索结果</h3>")
        
        for i, result in enumerate(results, 1):
            formatted.append("<div class='search-result'>")
            if include_source:
                formatted.append(f"<div class='search-source'>{result['source']}</div>")
            formatted.append(f"<a href='{result['link']}' target='_blank' class='search-title'>{result['title']}</a>")
            formatted.append(f"<div class='search-snippet'>{result['snippet']}</div>")
            formatted.append("</div>")
        
        formatted.append("</div>")
        return "\n".join(formatted)

    def get_sources_statistics(self) -> Dict[str, int]:
        """获取各搜索引擎的结果统计"""
        stats = {}
        for cache in self.result_cache.values():
            for item in cache:
                stats[item["source"]] = stats.get(item["source"], 0) + 1
        return stats
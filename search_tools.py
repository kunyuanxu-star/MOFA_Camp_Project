import asyncio
import aiohttp
from typing import List, Dict, Optional, Tuple
import json
from datetime import datetime
import hashlib
import base64
from cryptography.fernet import Fernet
from bs4 import BeautifulSoup

class DeepWebSearcher:
    """深网搜索工具"""
    def __init__(self, tor_proxy: str = None, i2p_proxy: str = None):
        self.tor_proxy = tor_proxy or "socks5://localhost:9050"
        self.i2p_proxy = i2p_proxy
        self.session = None
        self.encryption_key = Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0"

    async def initialize(self):
        """初始化深网会话"""
        connector = aiohttp.TCPConnector(force_close=True)
        self.session = aiohttp.ClientSession(
            connector=connector,
            headers={"User-Agent": self.user_agent}
        )

    async def close(self):
        """关闭会话"""
        if self.session:
            await self.session.close()

    def _encrypt_query(self, query: str) -> str:
        """加密搜索查询"""
        return self.cipher.encrypt(query.encode()).decode()

    def _decrypt_response(self, encrypted: str) -> str:
        """解密响应数据"""
        return self.cipher.decrypt(encrypted.encode()).decode()

    async def _fetch_tor(self, url: str) -> Optional[str]:
        """通过Tor网络获取内容"""
        try:
            async with self.session.get(
                url, 
                proxy=self.tor_proxy,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    return await resp.text()
        except Exception as e:
            print(f"Tor请求出错: {str(e)}")
        return None

    async def search_tor(self, query: str, engine: str = "ahmia") -> List[Dict]:
        """通过Tor网络搜索"""
        if not self.session:
            await self.initialize()

        results = []
        try:
            if engine == "ahmia":
                url = f"http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion/search/?q={query}"
                html = await self._fetch_tor(url)
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    for result in soup.select('.result'):
                        title = result.select_one('.title')
                        link = result.select_one('.link')
                        desc = result.select_one('.description')
                        if title and link:
                            results.append({
                                "title": title.get_text().strip(),
                                "link": link.get('href', '').strip(),
                                "snippet": desc.get_text().strip() if desc else "",
                                "source": "Tor (Ahmia)"
                            })
            
            elif engine == "torch":
                url = f"http://xmh57jrzrnw6insl.onion/4a1f6b371c/search.cgi?q={query}"
                html = await self._fetch_tor(url)
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    for result in soup.select('dt'):
                        title = result.find('a')
                        if title:
                            results.append({
                                "title": title.get_text().strip(),
                                "link": title.get('href', '').strip(),
                                "snippet": "",
                                "source": "Tor (Torch)"
                            })
        
        except Exception as e:
            print(f"Tor搜索出错: {str(e)}")
        
        return results[:5]

    async def search_i2p(self, query: str) -> List[Dict]:
        """通过I2P网络搜索"""
        if not self.session or not self.i2p_proxy:
            return []

        results = []
        try:
            url = f"http://udhdrtrcetjm5sxzskjyr5ztpeszydbh4dpl3pl4utgqqw2v4jna.b32.i2p/search?q={query}"
            async with self.session.get(
                url, 
                proxy=self.i2p_proxy,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    for result in soup.select('.result'):
                        title = result.select_one('h3 a')
                        if title:
                            results.append({
                                "title": title.get_text().strip(),
                                "link": title.get('href', '').strip(),
                                "snippet": "",
                                "source": "I2P"
                            })
        except Exception as e:
            print(f"I2P搜索出错: {str(e)}")
        
        return results[:5]

class MetaSearchEngine:
    def __init__(self, search_apis: Dict[str, dict], deepweb_config: Dict = None):
        """
        元搜索引擎(包含深网搜索)
        
        参数:
            search_apis: 明网搜索引擎配置
            deepweb_config: 深网配置 {
                "enable": True,
                "tor_proxy": "socks5://localhost:9050",
                "i2p_proxy": "http://localhost:4444",
                "warning": "自定义警告信息"
            }
        """
        self.search_apis = search_apis
        self.deepweb_config = deepweb_config or {}
        self.timeout = 15
        self.session = None
        self.deepweb_searcher = None
        self.cache = {}
        
        if self.deepweb_config.get("enable"):
            self.deepweb_searcher = DeepWebSearcher(
                tor_proxy=self.deepweb_config.get("tor_proxy"),
                i2p_proxy=self.deepweb_config.get("i2p_proxy")
            )

    async def initialize(self):
        """初始化所有搜索会话"""
        self.session = aiohttp.ClientSession()
        if self.deepweb_searcher:
            await self.deepweb_searcher.initialize()

    async def close(self):
        """关闭所有会话"""
        if self.session:
            await self.session.close()
        if self.deepweb_searcher:
            await self.deepweb_searcher.close()

    def _get_cache_key(self, query: str, mode: str) -> str:
        """生成缓存键"""
        return hashlib.sha256(f"{query}:{mode}".encode()).hexdigest()

    async def _fetch_surface_web(self, engine: str, query: str) -> List[Dict]:
        """获取明网搜索结果"""
        api_config = self.search_apis.get(engine)
        if not api_config:
            return []

        params = {
            "q": query,
            "api_key": api_config["api_key"],
            "num": 5
        }

        try:
            async with self.session.get(
                api_config["endpoint"],
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                if resp.status == 200:
                    return self._normalize_results(engine, await resp.json())
                return []
        except Exception as e:
            print(f"{engine}搜索出错: {str(e)}")
            return []

    async def _fetch_deep_web(self, query: str) -> List[Dict]:
        """获取深网搜索结果"""
        if not self.deepweb_searcher:
            return []

        results = []
        try:
            # Tor网络搜索
            tor_results = await self.deepweb_searcher.search_tor(query)
            results.extend(tor_results)
            
            # I2P网络搜索
            i2p_results = await self.deepweb_searcher.search_i2p(query)
            results.extend(i2p_results)
            
        except Exception as e:
            print(f"深网搜索出错: {str(e)}")
        
        return results

    def _normalize_results(self, engine: str, data: Dict) -> List[Dict]:
        """标准化不同来源的结果"""
        normalized = []
        
        if engine == "google":
            for item in data.get("organic_results", []):
                normalized.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "source": "Google",
                    "type": "surface",
                    "score": self._calculate_score(item)
                })
        elif engine == "bing":
            for item in data.get("webPages", {}).get("value", []):
                normalized.append({
                    "title": item.get("name", ""),
                    "link": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                    "source": "Bing",
                    "type": "surface",
                    "score": self._calculate_score(item)
                })
        
        return normalized

    def _calculate_score(self, item: Dict) -> float:
        """计算结果相关性分数"""
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        return (len(title) * 0.6 + len(snippet) * 0.4) / 100

    async def meta_search(self, query: str, mode: str = "mixed") -> Dict[str, List[Dict]]:
        """
        执行元搜索
        
        参数:
            query: 搜索查询
            mode: surface/deep/mixed
            
        返回:
            {
                "surface": [...],  # 明网结果
                "deepweb": [...]   # 深网结果
            }
        """
        cache_key = self._get_cache_key(query, mode)
        if cache_key in self.cache:
            return self.cache[cache_key]

        if not self.session:
            await self.initialize()

        # 并行获取所有结果
        tasks = []
        if mode in ("surface", "mixed"):
            tasks.extend([
                self._fetch_surface_web(engine, query) 
                for engine in self.search_apis.keys()
            ])
        
        deepweb_task = []
        if mode in ("deep", "mixed"):
            deepweb_task = self._fetch_deep_web(query)
        
        surface_results = []
        if tasks:
            for results in await asyncio.gather(*tasks):
                surface_results.extend(results)
        
        deepweb_results = await deepweb_task if deepweb_task else []
        
        # 合并结果
        combined = {
            "surface": sorted(surface_results, key=lambda x: x["score"], reverse=True)[:10],
            "deepweb": deepweb_results[:5]
        }
        
        # 缓存结果
        self.cache[cache_key] = combined
        return combined

    def format_results(self, results: Dict) -> str:
        """格式化搜索结果"""
        formatted = ["<div class='search-results'>"]
        
        # 明网结果
        if results["surface"]:
            formatted.append("<h3>🌐 明网搜索结果</h3>")
            for i, result in enumerate(results["surface"], 1):
                formatted.append(self._format_result_item(i, result))
        
        # 深网结果
        if results["deepweb"]:
            formatted.append("<h3 class='mt-3'>🕶️ 深网搜索结果</h3>")
            warning = self.deepweb_config.get("warning", 
                "注意: 深网链接需要Tor/I2P浏览器访问")
            formatted.append(f"<div class='alert alert-warning'>{warning}</div>")
            for i, result in enumerate(results["deepweb"], 1):
                formatted.append(self._format_result_item(i, result, True))
        
        formatted.append("</div>")
        return "\n".join(formatted)

    def _format_result_item(self, index: int, result: Dict, is_deepweb: bool = False) -> str:
        """格式化单个结果项"""
        return f"""
        <div class='search-result p-2 mb-2 {'deepweb-result' if is_deepweb else 'bg-white'}'>
            <div class='result-header d-flex justify-content-between mb-1'>
                <span class='result-index fw-bold'>{index}.</span>
                <span class='result-source badge {'bg-dark' if is_deepweb else 'bg-info'}>
                    {result['source']}
                </span>
            </div>
            <a href='{result['link']}' target='_blank' 
               class='result-title d-block fw-bold mb-1 {'onion-link' if is_deepweb else ''}'>
                {result['title']}
            </a>
            <div class='result-snippet small text-muted'>
                {result.get('snippet', '无描述')}
            </div>
        </div>"""
# MOFA_Camp_Project

# 一个AI智能体系统

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![Flask Version](https://img.shields.io/badge/flask-2.0%2B-lightgrey)
![OpenAI](https://img.shields.io/badge/OpenAI-gpt--3.5-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

## 目录
- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
  - [环境准备](#环境准备)
  - [安装步骤](#安装步骤)
  - [运行应用](#运行应用)
- [配置选项](#配置选项)
- [使用指南](#使用指南)
  - [基本命令](#基本命令)
  - [搜索模式](#搜索模式)
- [开发指南](#开发指南)
  - [扩展搜索引擎](#扩展搜索引擎)
  - [添加新工具](#添加新工具)
- [技术栈](#技术栈)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

## 功能特性

- 🔍 **混合搜索能力**：同时搜索明网(Google/Bing)和深网(Tor/I2P)资源
- 🧠 **自主决策**：根据任务自动选择最佳搜索策略
- 📝 **记忆管理**：记录对话历史、目标和学习经验
- 🤖 **任务自动化**：分解复杂目标为可执行步骤
- 🔒 **安全设计**：深网查询加密和代理隔离
- 💬 **交互式Web界面**：直观的聊天式交互体验
- 🌐 **多引擎支持**：集成多个主流搜索引擎
- 🔄 **自我优化**：通过反思机制持续改进表现

## 系统架构

```bash
project/
├── app.py                # Flask主应用(后端入口)
├── agent_core.py         # 智能体核心逻辑
├── search_tools.py       # 搜索引擎实现
├── templates/
│   └── index.html        # 前端界面
├── static/
│   └── styles.css        # 样式表
├── requirements.txt      # Python依赖列表
├── .env.example          # 环境配置示例
└── README.md             # 项目文档
```

## 快速开始

### 环境准备

1. Python 3.8或更高版本
2. Tor服务(用于深网搜索)
3. OpenAI API账号
4. (可选) I2P路由器(用于I2P网络搜索)

### 安装步骤

bash

复制

```
# 克隆仓库
git clone https://github.com/your-repo/ai-agent.git
cd ai-agent

# 创建虚拟环境(推荐)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑.env文件填写你的API密钥
```

### 运行应用

bash

复制

```
# 启动Flask开发服务器
python app.py

# 生产环境推荐使用Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

访问 `http://localhost:5000` 使用Web界面

## 配置选项

在`.env`文件中配置：

ini

复制

```
# ===== 必需配置 =====
OPENAI_API_KEY=your_openai_api_key_here

# ===== 明网搜索引擎 =====
GOOGLE_API_KEY=your_google_api_key
BING_API_KEY=your_bing_api_key

# ===== 深网配置 =====
TOR_PROXY=socks5://localhost:9050  # Tor代理地址
I2P_PROXY=http://localhost:4444    # I2P代理地址
DEEPWEB_WARNING=深网内容需要特殊浏览器访问 # 深网警告信息

# ===== 性能配置 =====
MAX_SURFACE_RESULTS=10    # 明网最大结果数
MAX_DEEPWEB_RESULTS=5     # 深网最大结果数
MEMORY_LIMIT=1000         # 记忆条目限制
```

## 使用指南

### 基本命令

| 命令                 | 描述             | 示例                       |
| :------------------- | :--------------- | :------------------------- |
| `/goal <目标>`       | 设置长期目标     | `/goal 学习Python编程`     |
| `/execute <任务>`    | 执行具体任务     | `/execute 查找Python教程`  |
| `/search <查询>`     | 明网搜索         | `/search 最新AI新闻`       |
| `/deepsearch <查询>` | 深网搜索         | `/deepsearch 隐私保护工具` |
| `/reflect`           | 自我反思总结经验 | `/reflect`                 |
| `/capabilities`      | 查看智能体能力   | `/capabilities`            |
| `/clear <类型>`      | 清除记忆         | `/clear goals`             |

### 搜索模式

1. **明网模式**
   - 仅搜索常规网络资源
   - 自动使用配置的搜索引擎(Google/Bing)
   - 示例：`/search 天气预报`
2. **深网模式**
   - 仅搜索.onion/.i2p站点
   - 需要Tor/I2P服务支持
   - 示例：`/deepsearch 隐私论坛`
3. **混合模式**(默认)
   - 同时搜索明网和深网
   - 自动去重和排序结果
   - 示例：`/execute 查找网络安全工具`

## 开发指南

### 扩展搜索引擎

1. 在`search_tools.py`中添加新引擎类：

python

复制

```
class NewSearchEngine:
    async def search(self, query: str) -> List[Dict]:
        # 实现搜索逻辑
        return formatted_results
```

1. 在`MetaSearchEngine`类中集成新引擎：

python

复制

```
async def _fetch_from_engine(self, engine: str, query: str):
    if engine == "new_engine":
        return await NewSearchEngine().search(query)
```

1. 更新`SEARCH_APIS`配置：

python

复制

```
SEARCH_APIS = {
    "new_engine": {
        "api_key": os.getenv("NEW_ENGINE_KEY"),
        "endpoint": "https://api.newengine.com"
    }
}
```

### 添加新工具

1. 在`agent_core.py`中添加工具方法：

python

复制

```
def _new_tool(self, param1: str, param2: int) -> str:
    """工具描述
    Args:
        param1: 参数说明
        param2: 参数说明
    Returns:
        执行结果描述
    """
    # 工具实现
    return result
```

1. 在`_initialize_tools`中注册工具：

python

复制

```
self.tools['new_tool'] = self._new_tool
```

1. 更新前端界面(如需要)

## 技术栈

| 组件     | 技术选择                        |
| :------- | :------------------------------ |
| 后端框架 | Flask + aiohttp                 |
| 前端框架 | Bootstrap 5                     |
| AI引擎   | OpenAI GPT-3.5                  |
| 明网搜索 | Google Custom Search + Bing API |
| 深网搜索 | Tor + I2P                       |
| 数据加密 | Fernet (AES-128)                |
| 异步处理 | asyncio                         |
| 部署方案 | Gunicorn + Nginx                |

## 贡献指南

1. Fork本项目仓库
2. 创建特性分支 (`git checkout -b feature/your-feature`)
3. 提交更改 (`git commit -am 'Add some feature'`)
4. 推送到分支 (`git push origin feature/your-feature`)
5. 创建Pull Request

**代码规范**：

- 遵循PEP 8编码规范
- 所有函数必须有类型注解和文档字符串
- 新功能必须包含单元测试

## 许可证

本项目采用 [MIT License](https://license/)。
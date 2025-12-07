# Agentic ChatBot - 通用智能对话机器人平台

<div align="center">

**基于 LangChain 1.0 架构的通用 AI 助手平台**

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![LangChain](https://img.shields.io/badge/LangChain-1.0-green.svg)](https://python.langchain.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)

[快速开始](#-快速开始) • [功能特性](#-核心功能) • [文档](#-文档) • [示例](#-使用示例)

</div>

---

## 🎯 项目简介

Agentic ChatBot 是一个**开箱即用、高度可集成**的智能对话机器人平台，让**任何产品都能快速拥有 AI 助手**。

**核心定位**：**"Cursor 的强大功能 + 可集成性 + 应用操作能力"**

### 🚀 核心价值

**快速让任何应用集成 AI 助手，不仅能专业问答，更能辅助用户操作应用，提升效率**

- 🎯 **快速集成** - 通过 SDK/API 可快速集成到任何应用（Web、桌面、移动端、IDE、企业系统）
- 💬 **专业问答** - 基于 RAG 技术，精准回答领域专业问题
- 🛠️ **操作辅助** - 通过工具调用，帮助用户自动化操作应用功能，提高工作效率
- 🔌 **开箱即用** - 既可独立使用，也可无缝嵌入现有产品

### 为什么选择 Agentic ChatBot？

- ✅ 借鉴 Cursor 的核心能力（@路径引用、上下文理解、智能对话）
- ✅ 提供 Cursor 做不到的：**开源 SDK，可嵌入任何产品**
- ✅ 不止于对话：**可调用工具，辅助用户操作应用**，如自动填表、数据查询、流程执行等
- ✅ 支持独立使用和快速集成两种方式

### 两种使用方式

1. **🚀 独立使用** - 无需任何集成，直接启动即可使用完整的 AI 对话功能
2. **🔌 快速集成** - 通过 SDK/API 轻松嵌入任何应用（Web、桌面、移动端、IDE），让你的产品瞬间拥有智能助手

### 技术栈

- **Backend**: FastAPI + LangChain 1.0 + LangGraph  
- **Agent**: `create_agent` + Middleware 架构
- **Frontend**: React + TypeScript + Vite  
- **AI**: OpenAI GPT-4o / Anthropic Claude 3.5  
- **Vector DB**: ChromaDB / FAISS  
- **协议**: MCP (Model Context Protocol)

### LangChain 1.0 核心特性

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware, PIIMiddleware
from langchain.tools import tool

@tool
def search_docs(query: str) -> str:
    """搜索文档库"""
    return f"搜索结果: {query}"

# 10 行代码创建生产级 Agent
agent = create_agent(
    model="gpt-4o",
    tools=[search_docs],
    system_prompt="你是一个有帮助的助手",
    middleware=[
        SummarizationMiddleware(model="gpt-4o-mini", trigger=("tokens", 4000)),
        PIIMiddleware("email", strategy="redact"),
    ],
)

result = agent.invoke({"messages": [{"role": "user", "content": "你好"}]})
```

---

## ✨ 核心功能

### 1. 🎯 智能问答能力
- 💬 **专业问答** - 基于 RAG 检索，精准回答领域专业问题
- 🧠 **上下文理解** - 理解多轮对话上下文，提供连贯回答
- 📚 **知识整合** - 融合文档、数据库、API 等多源知识

### 2. 🛠️ 应用操作辅助
- ⚡ **自动化操作** - 通过工具调用，帮助用户自动执行应用功能
- 🔧 **工具编排** - 智能选择和组合多个工具，完成复杂任务
- 🎨 **应用场景**：
  - 自动填写表单、提交数据
  - 数据库查询、报表生成
  - 文件处理、批量操作
  - 工作流程自动化

### 3. 🔌 快速集成能力
- 📦 **Python SDK** - 3 行代码即可集成到任何 Python 应用
- 🌐 **REST API** - 标准 HTTP 接口，支持任何编程语言
- 💻 **WebSocket** - 实时流式输出，提升用户体验
- 🔗 **示例支持** - 提供 Web、桌面、移动端集成示例

### 4. 🧠 LangChain 1.0 Agent 架构
- � `create_agent` 标准 ReAct 循环
- 🔄 丰富的内置 Middleware（历史压缩、PII 过滤、人工审批）
- � 基于 LangGraph 的持久化和流式输出
- 🛠️ 智能工具选择与编排

### 5. 💾 会话记忆管理
- 💬 短期记忆：多轮对话上下文
- 📚 长期记忆：用户偏好存储
- 🗜️ 自动压缩：SummarizationMiddleware 自动管理
- 🔒 隐私保护：PIIMiddleware 敏感信息过滤

### 6. 🔧 工具扩展 (MCP)
- 🔌 MCP 协议支持，轻松接入外部工具
- 🎯 `@tool` 装饰器快速定义工具
- 🔄 ToolRetryMiddleware 自动重试
- 🔒 安全沙箱执行

### 7. 🎯 三维上下文注入

| 方式 | 说明 | 应用场景示例 |
|------|------|------------|
| **RAG 检索** | 文档语义检索 | 产品手册问答、技术文档查询、知识库检索 |
| **MCP 服务器** | 数据库/API 接入 | 订单查询、数据统计、业务系统集成 |
| **@路径引用** | 本地文件引用 | 代码分析、配置文件读取、项目文档引用 |

### 💡 典型应用场景

#### 📊 企业内部系统
- **客服助手** - 自动回答产品问题 + 查询订单状态 + 提交工单
- **数据分析** - 理解自然语言查询 + 生成 SQL + 可视化结果
- **文档助手** - 检索技术文档 + 代码示例推荐

#### 🎨 产品应用
- **IDE 插件** - 代码解释 + Bug 修复建议 + 自动生成测试
- **电商平台** - 商品推荐 + 智能客服 + 订单处理
- **教育平台** - 答疑解惑 + 作业批改 + 学习路径规划

---

## 🎬 快速体验

### 3 分钟看懂如何集成

```python
# 步骤 1: 安装 SDK
pip install -e sdk/python

# 步骤 2: 集成到你的应用 (仅需 3 行代码!)
from chatbot_sdk import create_client

client = create_client(base_url="http://localhost:8000")
response = client.chat("帮我查询今天的订单数量")  # AI 自动调用工具查询数据库

# 步骤 3: 完成! 你的应用现在拥有了 AI 助手
```

**AI 能做什么？**
- ✅ 回答专业问题（基于你的文档库）
- ✅ 执行应用操作（调用你定义的工具/API）
- ✅ 理解上下文，多轮对话
- ✅ 提升用户效率 10 倍以上

---

## 🚀 快速开始

### 方式一：独立GUI模式（零代码）

适合非开发者或需要独立聊天界面的场景。

```bash
# 1. 克隆项目
git clone <repository-url>
cd agentic_chatBot

# 2. 配置上下文
cp config/config.json.example config.json
# 编辑 config.json，配置 RAG文档、@路径白名单、MCP工具

# 3. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 .env，设置 OPENAI_API_KEY

# 4. 启动（自动安装依赖）
source scripts/start.csh
# 或手动启动: python scripts/standalone_gui.py
```

访问 http://localhost:8000 即可使用完整的聊天界面！

**配置示例** (`config.json`):
```json
{
  "context": {
    "rag_sources": ["./docs", "./manual.pdf"],
    "path_whitelist": ["src/**/*.py"],
    "mcp_servers": [
      {"name": "database", "type": "sqlite", "config": {...}}
    ]
  }
}
```

---

### 方式二：SDK集成（代码调用）

适合开发者将AI能力集成到现有应用中。

#### 1. 安装 SDK

```bash
pip install -e sdk/python
```

#### 2. 初始化并调用

```python
from chatbot_sdk import create_client

# 创建客户端
client = create_client(
    app_id="your_app",
    app_secret="your_secret",
    base_url="http://localhost:8000",
    workspace_root="/path/to/workspace"
)

# 初始化
client.initialize()

# 聊天
response = client.chat("你好，请帮我分析数据")
print(response)

# 流式输出
for chunk in client.chat("生成报告", stream=True):
    if chunk["type"] == "text":
        print(chunk["content"], end="")
```

#### 3. 更多示例

```bash
# 运行集成示例
python examples/sdk_integration_examples.py --example all
```

---

### Docker 一键部署（生产环境）

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

服务地址：
- 前端: http://localhost:5173
- API: http://localhost:8000
- 文档: http://localhost:8000/docs

---

## 📋 配置说明

### 环境变量 (`.env`)

```env
# LLM配置 (必填)
OPENAI_API_KEY=sk-xxxxxxxx
OPENAI_MODEL=gpt-4-turbo-preview

# RAG配置
VECTOR_DB_TYPE=chroma
CHUNK_SIZE=1000
TOP_K_RETRIEVAL=5

# Agent配置
ENABLE_PLANNING=true
ENABLE_PATH_REFERENCE=true
MAX_ITERATIONS=10

# 工作区路径（用于@引用）
WORKSPACE_ROOT=/path/to/your/project
```

### 上下文配置 (`config.json`)

用于独立GUI模式，配置AI助手的知识来源：

```json
{
  "context": {
    "rag_sources": [
      "./docs",           // 文档目录
      "./manual.pdf"      // 单个文件
    ],
    "path_whitelist": [
      "src/**/*.py",      // 允许引用的文件模式
      "config/**"
    ],
    "mcp_servers": [
      {
        "name": "database",
        "type": "sqlite",
        "config": {
          "database_path": "./data.db"
        }
      }
    ]
  }
}
```

---

## 🔧 核心功能

### 1. 智能规划与执行
- 🧠 自动拆解复杂任务
- 🔄 LangGraph 状态机管理
- 🛠️ 智能工具选择与编排

### 2. 会话记忆管理
- 💬 短期记忆：多轮对话上下文
- 📚 长期记忆：用户偏好存储
- 🗂️ 项目上下文：文件关联

### 3. 工具扩展 (MCP)
- 🔌 MCP 协议支持
- 🔧 动态工具注册
- 🔒 安全沙箱执行

### 4. 三维上下文注入

| 方式 | 说明 | 示例 |
|------|------|------|
| **RAG 检索** | 文档语义检索 | 上传 PDF 后自动索引检索 |
| **@路径引用** | 本地文件引用 | `@src/config.py` |
| **MCP 工具** | 外部数据/API | 连接 SQLite、REST API |

> 💡 **深入了解**：查看 [上下文加载详解](docs/TARGET.md#-上下文加载详解核心差异化) 了解技术实现和使用场景

---

## 📚 文档

| 文档 | 说明 | 适合人群 |
|------|------|---------|
| [项目目标与架构](docs/TARGET.md) | 产品定位、系统架构、核心能力矩阵 | 技术决策者、架构师 |
| [功能实现状态](docs/FEATURE_STATUS.md) | 功能完成度和实现状态 | 开发者、贡献者 |
| [竞品分析](docs/COMPETITORS.md) | 同类型开源产品对比分析 | 技术决策者、产品经理 |
| [代码优化建议](docs/CODE_IMPROVEMENTS.md) | 代码改进和优化建议 | 开发者、贡献者 |
| [快速开始](docs/QUICKSTART.md) | 30分钟完成部署 | 所有用户 |
| [架构设计](docs/ARCHITECTURE.md) | 技术架构详解 | 开发者 |
| [集成指南](docs/INTEGRATION_GUIDE.md) | SDK集成教程 | 开发者 |

> 💡 **新手指南**：首次使用建议先阅读 [项目目标](docs/TARGET.md) 了解两种集成方式的详细对比

---

## 🎯 使用场景

### 场景1：产品文档助手（独立GUI）
```bash
# 配置产品文档路径
echo '{"context": {"rag_sources": ["./product_docs"]}}' > config.json

# 启动
python standalone_gui.py
```

### 场景2：API集成（SDK）
```python
# 在FastAPI中集成
@app.post("/support")
async def support(question: str):
    return chatbot.chat(question, use_rag=True)
```

### 场景3：混合模式
- 前端：嵌入聊天iframe（GUI）
- 后端：SDK自动化处理（代码）
- 共享相同的上下文配置

> 💡 **更多场景**：查看 [项目目标文档](docs/TARGET.md#-快速上手) 了解详细的场景分析和混合使用方案

---

## 🔍 示例代码

查看 `examples/` 目录：

- `sdk_integration_examples.py` - SDK完整示例
- `desktop_app_integration.py` - 桌面应用集成

运行示例：
```bash
python examples/sdk_integration_examples.py
```

```bash
# 健康检查
curl http://localhost:8000/health

# API 文档
open http://localhost:8000/docs

# 发送消息
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'
```

---

## 📦 项目结构

```
backend/
├── app/
│   ├── api/              # API 路由（chat, documents, tools）
│   ├── core/             # 核心逻辑（agent, planner, executor）
│   ├── llm/              # LLM 客户端封装
│   ├── mcp/              # MCP 协议实现
│   ├── rag/              # RAG 检索系统
│   ├── models/           # 数据模型
│   ├── exceptions.py     # ✨ 自定义异常
│   ├── dependencies.py   # ✨ 依赖注入
│   ├── config.py         # 配置管理
│   └── main.py           # FastAPI 应用
├── config/               # 配置文件
├── data/                 # 数据目录（运行时生成）
├── logs/                 # 日志
├── tests/                # 测试
└── requirements.txt      # Python 依赖
```

---

## 🔌 集成示例

### Python SDK

```python
from chatbot_sdk import ChatBot

bot = ChatBot(api_url="http://localhost:8000")

# 简单对话
response = bot.chat("介绍一下你的功能")

# 启用 RAG
response = bot.chat("总结这份报告", use_rag=True)

# 流式响应
for chunk in bot.stream("写一个排序算法"):
    print(chunk, end="")
```

### TypeScript

```typescript
import { ChatBotClient } from '@chatbot/client';

const client = new ChatBotClient({
  apiUrl: 'ws://localhost:8000/api/v1/chat/ws'
});

await client.connect();
client.onMessage((msg) => console.log(msg));
await client.send('你好');
```

---

## 🧪 测试

```bash
cd backend

# 运行测试
pytest tests/ -v

# 测试覆盖率
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

---

## 🐳 Docker 部署

```bash
docker-compose up -d
```

---

## 📖 文档

| 文档 | 说明 |
|------|------|
| [TARGET.md](docs/TARGET.md) | 项目目标与技术选型 |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 系统架构设计 |
| [QUICKSTART.md](docs/QUICKSTART.md) | 5 分钟快速上手 |
| [INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md) | 集成指南 |
| [CRITICAL_CODE_FIXES.md](docs/archive/CRITICAL_CODE_FIXES.md) | 关键代码修复清单 |

---

## 🆕 最新优化 (2025-12-04)

- ✅ **异常处理体系** - 统一的异常类和错误处理
- ✅ **依赖注入** - 单例模式 + 健康检查
- ✅ **完善的 .gitignore** - 排除运行时生成文件
- ✅ **数据目录结构** - 自动创建必要的目录
- ✅ **增强的健康检查** - 详细的组件状态报告
- ✅ **全面的 README** - 完整的使用文档

---

## 🛠 配置说明

关键环境变量：

```bash
# LLM
OPENAI_API_KEY=sk-...              # 必填
OPENAI_MODEL=gpt-4-turbo-preview

# 向量数据库
VECTOR_DB_TYPE=chroma
CHROMA_PERSIST_DIR=./data/vector_db/chroma

# RAG
CHUNK_SIZE=1000
TOP_K_RETRIEVAL=5

# 安全
WORKSPACE_ROOT=.
ALLOWED_PATH_PATTERNS=**/*.py,**/*.md
MAX_FILE_SIZE_FOR_CONTEXT=10485760  # 10MB
```

完整配置参见 [.env.example](backend/.env.example)

---

## 🤝 贡献

欢迎贡献！请遵循以下步骤：

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

MIT License - 查看 [LICENSE](LICENSE) 了解详情

---

## 🙏 致谢

- [LangChain](https://github.com/langchain-ai/langchain) - LLM 应用框架
- [FastAPI](https://fastapi.tiangolo.com/) - Web 框架
- [MCP](https://modelcontextprotocol.io/) - 模型上下文协议

---

<div align="center">

**让每个应用都能拥有智能助理的能力** 🚀

基于 LangChain 1.0 架构 | Made with ❤️

</div>

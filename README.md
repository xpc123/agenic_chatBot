# Agentic ChatBot - 5 分钟给你的应用加上 Cursor 级别的 AI 助手

<div align="center">

**🚀 快速集成 • 🎯 开箱即用 • 💡 Cursor 级别体验**

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![LangChain](https://img.shields.io/badge/LangChain-1.0-green.svg)](https://python.langchain.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)

[⚡ 5分钟快速开始](docs/QUICKSTART.md) • [📚 功能特性](#-核心功能) • [🔌 集成示例](#-3-行代码集成) • [📖 完整文档](#-文档)

</div>

---

## ⚡ 30 秒看懂

### 核心理念：**上下文即能力**

```python
# 🎯 你只需要提供上下文，AI 自动获得能力
from app.core.context_manager import ContextManager

# IDE 产品？提供代码上下文
ctx = ContextManager.for_ide(
    workspace_path="/project",
    current_file="src/main.py",
    diagnostics=errors  # LSP 诊断信息
)

# 数据分析工具？提供数据上下文  
ctx = ContextManager.for_data_analysis(
    dataframe_info={"shape": (1000, 10), "columns": ["id", "name"]},
    query_history=["SELECT * FROM users"]
)

# 客服系统？提供用户上下文
ctx = ContextManager.for_customer_service(
    user_profile=user_info,
    order_history=orders
)

# 就这样！AI 理解了你的产品，拥有了相应能力
```

**✅ 你不需要理解**：
- ❌ LLM 模型原理
- ❌ RAG 检索技术
- ❌ Agent 规划算法

**✅ 你只需要知道**：
- ✅ **你的产品有什么数据？** → 提供上下文
- ✅ **什么最重要？** → 设置优先级
- ✅ **完成！** → AI 自动处理其余一切

[**→ 立即学习 Context 快速集成**](docs/CONTEXT_INTEGRATION.md)

---

## 🎯 核心定位

**"想要 5 分钟给你的应用加上 Cursor 级别的 AI 助手？我们来了！"**

Agentic ChatBot 是一个**轻量级、可快速集成**的智能对话机器人平台，让**任何产品都能拥有 Cursor 级别的 AI 能力**。

### 🎯 为什么选择我们？

| 维度 | Cursor/Copilot | mcp-agent-graph | **Agentic ChatBot** |
|------|----------------|-----------------|-------------------|
| **核心定位** | 代码编辑器 | 可视化工作流平台 | **快速集成的 AI 助手** |
| **集成时间** | ❌ 无法集成 | ⚠️ 需要部署完整平台 | ✅ **5 分钟** |
| **@路径引用** | ✅ | ❌ | ✅ **Cursor 风格** |
| **SDK 集成** | ❌ 闭源 | ⚠️ 有限支持 | ✅ **3 行代码** |
| **轻量化** | N/A | ❌ 需要 Docker+DB | ✅ **单文件部署** |
| **开源** | ❌ | ✅ | ✅ **MIT 协议** |
| **使用场景** | IDE 内使用 | 企业工作流 | **任何应用集成** |

### 🚀 核心优势

- 🎯 **Context 驱动** - 上下文即能力，产品方只需提供数据，AI 自动理解
- ⚡ **5 分钟集成** - 预设模板 + 链式调用，极简 API
- 🔧 **零 AI 知识要求** - 不需要理解 LLM/RAG/Agent，只需要了解你的产品
- 🔌 **真正可集成** - 提供 Python SDK、REST API、WebSocket
- 💡 **轻量化设计** - 无需 Docker，单文件即可运行
- 🛠️ **工具生态** - 内置 MCP 协议，可调用任何工具/API
- 📦 **开箱即用** - 既可独立使用，也可快速嵌入

### 💼 适用场景

| 场景 | 集成方式 | 用时 |
|------|---------|------|
| **产品内嵌 AI** | 3 行代码集成 SDK | 5 分钟 |
| **独立 AI 助手** | 启动服务 + 访问 UI | 3 分钟 |
| **企业客服系统** | REST API 集成 | 10 分钟 |
| **IDE 插件** | WebSocket 集成 | 20 分钟 |
| **数据分析工具** | SDK + 自定义工具 | 30 分钟 |

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

### 🎯 Context 快速集成（核心特性）

不同产品类型，使用不同的预设模板：

#### IDE / 代码编辑器
```python
from app.core.context_manager import ContextManager

ctx = ContextManager.for_ide(
    workspace_path="/project",
    current_file="src/main.py",
    diagnostics=[{"line": 10, "message": "undefined variable"}],
    git_info={"branch": "main", "modified_files": ["src/main.py"]}
)
# AI 自动理解代码上下文，提供代码建议
```

#### 数据分析工具
```python
ctx = ContextManager.for_data_analysis(
    dataframe_info={
        "shape": (1000, 10),
        "columns": ["id", "name", "age"],
        "dtypes": {"id": "int", "name": "str"}
    },
    query_history=["SELECT * FROM users WHERE age > 30"]
)
# AI 自动理解数据结构，生成分析代码
```

#### 客服系统
```python
ctx = ContextManager.for_customer_service(
    user_profile={"id": "U123", "vip_level": "gold"},
    order_history=[{"id": "O001", "status": "shipped"}],
    knowledge_base=knowledge_docs
)
# AI 自动理解用户信息，提供个性化服务
```

#### 自定义产品
```python
ctx = (ContextManager()
       .add_custom("app_state", current_state, priority="HIGH")
       .add_custom("user_data", user_info, priority="MEDIUM")
       .add_rag_results(knowledge_base))
# 完全自定义，适配任何产品
```

[**→ 查看完整 Context 集成指南**](docs/CONTEXT_INTEGRATION.md)

---

### 其他核心功能

#### @路径引用（Cursor 风格）
```python
# 像 Cursor 一样引用文件
response = bot.chat("@src/models/user.py 这个类有什么问题？")
```

#### RAG 知识库
```python
# 基于文档智能问答
bot.upload_document("./docs/product_manual.pdf")
response = bot.chat("我们产品的核心功能是什么？", use_rag=True)
```

#### 流式输出
```python
# 实时响应
for chunk in bot.chat_stream("写一个 Python Web 服务"):
    print(chunk, end="", flush=True)
```

[**→ 查看完整示例代码**](examples/quick_integration.py)

---

## 🚀 5 分钟快速开始

### ⚡ 方式一：一键安装（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/xpc123/agenic_chatBot.git
cd agenic_chatBot

# 2. 一键安装（自动完成所有配置）
chmod +x quick_install.sh
./quick_install.sh  # 或使用 quick_install.csh

# 3. 编辑配置，填入你的 API Key
vi backend/.env  # 设置 OPENAI_API_KEY

# 4. 启动服务
cd backend && source venv/bin/activate
python run.py

# ✅ 完成！服务已启动在 http://localhost:8000
```

**就这么简单！总共 5 分钟！**

### 🎯 方式二：3 行代码集成

```python
# 使用统一 SDK (支持嵌入模式和远程模式)
from agentic_sdk import ChatBot

# 嵌入模式（直接调用后端，无需启动服务）
bot = ChatBot()

# 或远程模式（通过 HTTP API）
bot = ChatBot(base_url="http://localhost:8000")

response = bot.chat("帮我分析 @src/user.py 这个文件")

# 🎉 完成！你的应用现在有了 Cursor 级别的 AI 助手
```

### 🔌 常见框架集成

<details>
<summary><b>Flask 集成</b></summary>

```python
from flask import Flask, request, jsonify
from agentic_sdk import ChatBot

app = Flask(__name__)
bot = ChatBot()  # 嵌入模式

@app.route('/api/chat', methods=['POST'])
def chat():
    message = request.json.get('message')
    response = bot.chat(message)
    return jsonify({'response': response.text})

if __name__ == '__main__':
    app.run(port=5000)
```
</details>

<details>
<summary><b>FastAPI 集成</b></summary>

```python
from fastapi import FastAPI
from pydantic import BaseModel
from agentic_sdk import ChatBot

app = FastAPI()
bot = ChatBot()  # 嵌入模式

class Query(BaseModel):
    message: str

@app.post("/api/chat")
async def chat(query: Query):
    response = bot.chat(query.message)
    return {"response": response.text}
```
</details>

<details>
<summary><b>React 前端集成</b></summary>

```tsx
import { useState } from 'react';

function ChatBot() {
    const [message, setMessage] = useState('');
    const [response, setResponse] = useState('');
    
    const sendMessage = async () => {
        const res = await fetch('http://localhost:8000/api/v1/chat/message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        const data = await res.json();
        setResponse(data.message);
    };
    
    return (
        <div>
            <input value={message} onChange={(e) => setMessage(e.target.value)} />
            <button onClick={sendMessage}>发送</button>
            <div>{response}</div>
        </div>
    );
}
```
</details>

[**→ 查看更多框架集成示例**](examples/framework_integrations.py)

---

## 🎨 3 行代码集成

### 基础用法

```python
from agentic_sdk import ChatBot

# 1. 初始化（嵌入模式 - 直接调用后端）
bot = ChatBot()

# 或远程模式
# bot = ChatBot(base_url="http://localhost:8000")

# 2. 发送消息
response = bot.chat("你好，介绍一下你的功能")

# 3. 完成！
print(response.text)
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
# SDK 已包含在项目中，无需额外安装
# 只需确保项目在 Python 路径中
```

#### 2. 初始化并调用

```python
from agentic_sdk import ChatBot, ChatConfig

# 嵌入模式（推荐 - 直接调用后端，无需启动服务）
bot = ChatBot()

# 或远程模式（需要先启动后端服务）
bot = ChatBot(base_url="http://localhost:8000")

# 聊天
response = bot.chat("你好，请帮我分析数据")
print(response.text)

# 流式输出
for chunk in bot.chat_stream("生成报告"):
    print(chunk.content, end="", flush=True)

# Settings API（对应 Gradio 设置界面）
bot.sync_index()                      # 同步索引
bot.add_rule("...", "user")           # 添加规则
bot.toggle_skill("code_review", True) # 切换技能
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
agenic_chatBot/
├── agentic_sdk/          # 🆕 统一 SDK（支持嵌入/远程双模式）
│   ├── __init__.py       # 包入口
│   ├── chatbot.py        # ChatBot 主类（双模式）
│   ├── config.py         # 配置类
│   ├── types.py          # 类型定义
│   ├── settings.py       # Settings 管理器
│   ├── remote_client.py  # 远程客户端（HTTP API）
│   └── README.md         # SDK 文档
├── backend/
│   ├── app/
│   │   ├── api/          # API 路由（chat, documents, tools, settings）
│   │   ├── core/         # 核心逻辑（orchestrator, planner, executor）
│   │   ├── llm/          # LLM 客户端封装
│   │   ├── mcp/          # MCP 协议实现
│   │   ├── rag/          # RAG 检索系统
│   │   ├── models/       # 数据模型
│   │   └── config.py     # 配置管理
│   ├── data/             # 数据目录
│   └── requirements.txt  # Python 依赖
├── scripts/              # 启动脚本
│   └── app.py            # Gradio UI（使用统一 SDK）
├── docs/                 # 文档
├── examples/             # 示例代码
└── tests/                # 测试
```

---

## 🔌 集成示例

### Python SDK（统一 SDK）

```python
from agentic_sdk import ChatBot, ChatConfig

# 嵌入模式（推荐）
bot = ChatBot()

# 远程模式
bot = ChatBot(base_url="http://localhost:8000")

# 简单对话
response = bot.chat("介绍一下你的功能")
print(response.text)

# RAG 自动启用（如果配置了）
response = bot.chat("总结这份报告")
print(response.sources)  # 显示来源

# 流式响应
for chunk in bot.chat_stream("写一个排序算法"):
    print(chunk.content, end="", flush=True)

# Settings API
status = bot.get_index_status()       # 获取索引状态
bot.sync_index(force=True)            # 强制重建索引
skills = bot.list_skills()            # 列出技能
bot.toggle_skill("code_review", True) # 启用技能
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

### 快速开始
| 文档 | 说明 | 适合人群 |
|------|------|----------|
| [**CONTEXT_INTEGRATION.md**](docs/CONTEXT_INTEGRATION.md) | **Context 快速集成指南** ⭐ | **所有产品集成者（必读）** |
| [QUICKSTART.md](docs/QUICKSTART.md) | 5 分钟快速上手 | 新用户 |

### 核心文档
| 文档 | 说明 |
|------|------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 系统架构设计 |
| [LANGCHAIN_1.0.md](docs/LANGCHAIN_1.0.md) | LangChain 1.0 技术详解 |
| [FEATURE_STATUS.md](docs/FEATURE_STATUS.md) | 功能实现状态 |
| [SETUP.md](docs/SETUP.md) | 安装配置指南 |

### 参考文档
| 文档 | 说明 |
|------|------|
| [COMPETITORS.md](docs/COMPETITORS.md) | 竞品分析 |
| [agentic_sdk README](agentic_sdk/README.md) | 🆕 统一 SDK 文档（嵌入/远程双模式） |
| [Examples](examples/README.md) | 集成示例代码 |

---

## 🆕 最新优化 (2025-01-05)

### 🎯 纯 ReAct 模式 (NEW!)

采用业界标准的 **ReAct (Reasoning + Acting)** 模式，LLM 自主决策是否使用工具：

```
用户请求 → Thought (分析) → Action (工具调用) → Observation (结果) → ... → Final Answer
```

**优势**：
- ✅ **更高准确性** - LLM 自主推理，无预判断偏差
- ✅ **更强灵活性** - 支持多轮工具调用，解决复杂问题
- ✅ **可解释性** - Thought 显示完整推理过程
- ✅ **容错能力** - 工具失败时 LLM 可调整策略

### 📊 测试评估体系 (NEW!)

完整的测试框架，对标 Cursor/Copilot：

```bash
# 运行综合测试 (26 用例)
python tests/test_sdk_comprehensive.py

# 运行回归测试 (10 黄金用例)
python tests/regression/test_regression.py

# 运行能力评估
python -m tests.evaluation.eval_framework
```

**评估维度**：
| 指标 | 目标 | 当前得分 |
|------|------|----------|
| 工具使用准确性 | ≥95% | 100% ✅ |
| 响应相关性 | ≥90% | 90.8% ✅ |
| 错误处理 | ≥95% | 100% ✅ |
| 延迟评分 | ≥70% | 61.3% ⚠️ |

### 其他优化

- ✅ **JedAI Token 缓存** - 避免重复登录，提升性能
- ✅ **异常处理体系** - 统一的异常类和错误处理
- ✅ **依赖注入** - 单例模式 + 健康检查
- ✅ **完善的 .gitignore** - 排除运行时生成文件
- ✅ **数据目录结构** - 自动创建必要的目录
- ✅ **增强的健康检查** - 详细的组件状态报告

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

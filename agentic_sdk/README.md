# Agentic ChatBot SDK

通用可嵌入的 AI 助手 SDK，支持**嵌入模式**和**远程模式**。

## 🎯 特性

- ✅ **双模式架构** - 嵌入模式（直接调用）+ 远程模式（HTTP API）
- ✅ **统一 API** - 无论哪种模式，接口完全一致
- ✅ **完整功能** - Chat、RAG、Memory、Skills、Tools、MCP
- ✅ **Settings API** - 索引、规则、技能、MCP 管理

## 🚀 快速开始

### 嵌入模式（默认）

适用于 Python 应用直接集成：

```python
from agentic_sdk import ChatBot

# 创建实例（嵌入模式）
bot = ChatBot()

# 同步对话
response = bot.chat("你好")
print(response.text)

# 流式对话
for chunk in bot.chat_stream("讲个故事"):
    print(chunk.content, end="", flush=True)
```

### 远程模式

适用于非 Python 应用或分布式部署：

```python
from agentic_sdk import ChatBot, ChatConfig

# 方式1：快捷参数
bot = ChatBot(base_url="http://localhost:8000")

# 方式2：配置对象
config = ChatConfig.remote(
    base_url="http://localhost:8000",
    app_id="my_app",
    app_secret="secret",
)
bot = ChatBot(config)

# API 完全一致
response = bot.chat("你好")
print(response.text)
```

## 📦 架构

```
┌─────────────────────────────────────────────────────────────┐
│                     客户应用                                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│                   agentic_sdk.ChatBot                        │
│                                                              │
│  ┌─────────────────┐       ┌─────────────────┐              │
│  │   嵌入模式       │       │   远程模式       │              │
│  │  (直接调用)      │       │  (HTTP API)     │              │
│  └────────┬────────┘       └────────┬────────┘              │
│           │                         │                        │
│           ▼                         ▼                        │
│  ┌─────────────────┐       ┌─────────────────┐              │
│  │ CursorStyle     │       │ RemoteClient    │              │
│  │ Orchestrator    │       │ (HTTP)          │              │
│  └────────┬────────┘       └────────┬────────┘              │
│           │                         │                        │
└───────────┼─────────────────────────┼────────────────────────┘
            │                         │
            ▼                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend / Core Engine                     │
│  • CursorStyleOrchestrator                                  │
│  • RAG / Memory / Skills / Tools / MCP                      │
│  • Settings API                                             │
└─────────────────────────────────────────────────────────────┘
```

## ⚙️ Settings API

统一的设置管理接口，对应 Gradio Settings UI：

```python
from agentic_sdk import ChatBot

bot = ChatBot()

# === 索引管理 ===
status = bot.get_index_status()
bot.sync_index(force=True)
bot.clear_index()

# === 规则管理 ===
rules = bot.get_rules()
bot.add_rule("Always respond in Chinese", "user")
bot.remove_rule("Always respond in Chinese", "user")

# === 技能管理 ===
skills = bot.list_skills()
bot.toggle_skill("code_review", enabled=True)
bot.create_skill(
    skill_id="my_skill",
    name="My Skill",
    description="A custom skill",
    instructions="...",
    triggers=["trigger1", "trigger2"],
)
bot.delete_skill("my_skill")

# === MCP 服务器管理 ===
servers = bot.list_mcp_servers()
bot.add_mcp_server("github", "sse", "http://localhost:3000")
bot.remove_mcp_server("github")

# === 摘要 ===
summary = bot.get_settings_summary()
```

## 🔧 自定义工具

```python
from agentic_sdk import ChatBot

bot = ChatBot()

@bot.tool
def get_weather(city: str) -> str:
    """获取城市天气"""
    return f"{city}: 晴，25°C"

response = bot.chat("北京天气怎么样？")
```

## 📚 知识库 (RAG)

```python
from agentic_sdk import ChatBot

bot = ChatBot()

# 加载文档
bot.load_documents(["./docs/manual.pdf", "./docs/faq/"])

# 对话（自动使用知识库）
response = bot.chat("产品如何安装？")
print(response.sources)  # 显示来源
```

## ⚙️ 配置

```python
from agentic_sdk import ChatBot, ChatConfig

# 预设配置
config = ChatConfig.minimal()   # 仅对话
config = ChatConfig.full()      # 所有功能
config = ChatConfig.embedded()  # 嵌入模式
config = ChatConfig.remote("http://localhost:8000")  # 远程模式

# 完整配置
config = ChatConfig(
    mode="embedded",      # "embedded" 或 "remote"
    enable_rag=True,
    enable_memory=True,
    enable_skills=True,
    enable_mcp=True,
)

bot = ChatBot(config)
```

## 📂 目录结构

```
agentic_sdk/
├── __init__.py       # 包入口
├── chatbot.py        # ChatBot 主类（双模式）
├── config.py         # 配置类
├── types.py          # 类型定义
├── settings.py       # Settings 管理器
├── remote_client.py  # 远程客户端
├── server.py         # HTTP API 服务器
└── ui.py             # Gradio UI
```

## 🔗 Settings API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/settings/indexing/status` | GET | 索引状态 |
| `/api/v1/settings/indexing/sync` | POST | 同步索引 |
| `/api/v1/settings/indexing` | DELETE | 清除索引 |
| `/api/v1/settings/rules` | GET/POST/DELETE | 规则管理 |
| `/api/v1/settings/skills` | GET/POST | 技能列表/创建 |
| `/api/v1/settings/skills/{id}` | GET/PATCH/DELETE | 技能详情/更新/删除 |
| `/api/v1/settings/skills/{id}/toggle` | POST | 启用/禁用技能 |
| `/api/v1/settings/mcp` | GET/POST | MCP 服务器列表/添加 |
| `/api/v1/settings/mcp/{name}` | DELETE | 删除 MCP 服务器 |
| `/api/v1/settings/summary` | GET | 设置摘要 |

## 🎨 Gradio UI

```bash
# 启动 Gradio UI
python scripts/app.py

# 访问 http://localhost:7870
```

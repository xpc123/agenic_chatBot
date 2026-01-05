# Agentic ChatBot SDK

通用可嵌入的 AI 助手 SDK。

## 🚀 快速开始

### Python SDK 集成

```python
from agentic_sdk import ChatBot

# 创建实例
bot = ChatBot()

# 同步对话
response = bot.chat("你好")
print(response.text)

# 流式对话
for chunk in bot.chat_stream("讲个故事"):
    print(chunk.content, end="", flush=True)
```

### HTTP API 集成

```bash
# 启动服务器
python -m agentic_sdk.server --host 0.0.0.0 --port 8000

# 调用 API
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "session_id": "test"}'
```

### Gradio UI

```bash
# 启动 UI
python -m agentic_sdk.ui --host 0.0.0.0 --port 7860
```

## 📦 架构

```
┌─────────────────────────────────────────────────────────────┐
│                     客户应用                                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  方式1: Python SDK           方式2: HTTP API                 │
│  from agentic_sdk import     POST /api/chat                 │
│  ChatBot                     GET /api/chat/stream           │
│                                                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   Core Engine                               │
│  • CursorStyleOrchestrator                                  │
│  • IntentRecognizer                                         │
│  • AgentLoop                                                │
│  • RAG / Memory / Skills / Tools                            │
└─────────────────────────────────────────────────────────────┘
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
```

## ⚙️ 配置

```python
from agentic_sdk import ChatBot, ChatConfig

# 完整配置
config = ChatConfig(
    enable_rag=True,
    enable_memory=True,
    enable_skills=True,
    enable_mcp=True,
)

# 或使用预设
config = ChatConfig.minimal()  # 仅对话
config = ChatConfig.full()     # 所有功能

bot = ChatBot(config)
```

## 📂 目录结构

```
agentic_sdk/
├── __init__.py      # 包入口
├── chatbot.py       # ChatBot 主类
├── config.py        # 配置类
├── types.py         # 类型定义
├── server.py        # HTTP API 服务器
└── ui.py            # Gradio UI (可选)
```

## 🔗 API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/chat` | POST | 同步对话 |
| `/api/chat/stream` | POST | 流式对话 (SSE) |
| `/api/tools` | GET | 列出工具 |
| `/api/skills` | GET | 列出技能 |
| `/api/sessions` | GET | 列出会话 |
| `/api/sessions/{id}` | DELETE | 清除会话 |
| `/api/knowledge/search` | POST | 搜索知识库 |


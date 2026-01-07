# SDK 目录已废弃

⚠️ **此目录已废弃**

所有功能已合并到 `agentic_sdk` 模块中。

## 迁移指南

### 旧方式（已废弃）

```python
from sdk.python.chatbot_sdk import AgenticChatBotSDK

sdk = AgenticChatBotSDK(
    base_url="http://localhost:8000",
    app_id="my_app",
    app_secret="secret",
)
response = sdk.chat("你好")
```

### 新方式（推荐）

```python
from agentic_sdk import ChatBot, ChatConfig

# 远程模式
bot = ChatBot(base_url="http://localhost:8000")
# 或
config = ChatConfig.remote("http://localhost:8000", app_id="my_app", app_secret="secret")
bot = ChatBot(config)

# 嵌入模式
bot = ChatBot()  # 默认嵌入模式

response = bot.chat("你好")
print(response.text)
```

## 主要变化

| 功能 | 旧 SDK | 新 SDK |
|------|--------|--------|
| 同步对话 | `sdk.chat()` | `bot.chat()` |
| 流式对话 | `sdk.chat_stream()` | `bot.chat_stream()` |
| 设置管理 | ❌ | ✅ `bot.get_index_status()` 等 |
| 嵌入模式 | ❌ | ✅ 直接调用后端 |
| 远程模式 | ✅ HTTP API | ✅ HTTP API |

## 更多信息

请参阅 `agentic_sdk` 目录的 README 获取完整文档。




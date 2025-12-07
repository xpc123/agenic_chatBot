# Agentic ChatBot - Python SDK

> **30秒集成AI助手到你的应用**

## 🚀 快速开始

### 安装

```bash
pip install agentic-chatbot-sdk
# 或从源码安装
pip install -e /path/to/agentic_chatBot/sdk/python
```

### 基础使用

```python
from chatbot_sdk import create_client

# 1. 创建客户端
client = create_client(
    app_id="your_app",
    app_secret="your_secret",
    base_url="http://localhost:8000"
)

# 2. 初始化
client.initialize()

# 3. 聊天
response = client.chat("你好，请介绍一下自己")
print(response)
```

## 📖 核心功能

### 1. 基础对话

```python
# 普通对话
response = client.chat("今天天气怎么样？")

# 流式输出
for chunk in client.chat("写一首诗", stream=True):
    if chunk["type"] == "text":
        print(chunk["content"], end="", flush=True)

# 带会话ID（保持上下文）
response = client.chat(
    "继续上一个话题",
    session_id="user_123"
)
```

### 2. RAG知识库集成

```python
# 上传文档
client.upload_document(
    content="产品使用说明...",
    filename="manual.md",
    metadata={"version": "1.0", "category": "docs"}
)

# 基于知识库提问
response = client.chat(
    "如何使用XX功能？",
    use_rag=True  # 启用RAG检索
)

# 批量上传
for file in ["doc1.md", "doc2.pdf", "doc3.txt"]:
    client.upload_file(file)
```

### 3. @路径引用

```python
# 配置工作区
client = create_client(
    app_id="your_app",
    app_secret="secret",
    workspace_root="/path/to/project"  # 设置工作区根目录
)

# 引用本地文件
response = client.chat("请分析 @/src/main.py 的代码")

# 引用多个文件
response = client.chat("""
请对比以下文件的区别：
- @/config/dev.yml
- @/config/prod.yml
""")
```

### 4. 自定义MCP工具

```python
# 注册工具
client.register_tool(
    name="query_database",
    description="查询业务数据库",
    parameters={
        "type": "object",
        "properties": {
            "sql": {"type": "string", "description": "SQL查询语句"},
            "limit": {"type": "integer", "description": "返回数量限制"}
        },
        "required": ["sql"]
    },
    endpoint="https://your-app.com/api/db/query",
    auth={"type": "bearer", "token": "your_token"}
)

# AI会自动调用工具
response = client.chat("查询最近的订单数据")

# 列出所有工具
tools = client.list_tools()
```

### 5. 高级配置

```python
from chatbot_sdk import ChatBotSDK, ChatBotConfig

config = ChatBotConfig(
    app_id="your_app",
    app_secret="secret",
    base_url="http://localhost:8000",
    
    # 工作区配置
    workspace_root="/path/to/workspace",
    
    # MCP服务器
    mcp_servers=[
        {
            "name": "database_tools",
            "url": "http://localhost:9000"
        }
    ],
    
    # RAG配置
    rag_config={
        "chunk_size": 500,
        "top_k": 3,
        "similarity_threshold": 0.7
    },
    
    # Webhook回调
    webhook_url="https://your-app.com/webhook",
    
    # 超时设置
    timeout=60
)

client = ChatBotSDK(config)
```

## 🎯 集成场景

### 场景1：FastAPI集成

```python
from fastapi import FastAPI
from chatbot_sdk import create_client

app = FastAPI()

# 初始化chatbot
chatbot = create_client("app_id", "secret")
chatbot.initialize()

@app.post("/api/support")
async def customer_support(question: str, user_id: str):
    """客户支持接口"""
    response = chatbot.chat(
        message=question,
        session_id=user_id,
        use_rag=True  # 使用产品知识库
    )
    return {"answer": response}

@app.post("/api/analyze")
async def analyze_data(file_path: str):
    """数据分析接口"""
    response = chatbot.chat(f"请分析 @{file_path} 的数据")
    return {"analysis": response}
```

### 场景2：Django集成

```python
# views.py
from django.http import JsonResponse
from chatbot_sdk import create_client

chatbot = create_client("app_id", "secret")
chatbot.initialize()

def chat_api(request):
    message = request.POST.get('message')
    response = chatbot.chat(message, use_rag=True)
    return JsonResponse({"response": response})
```

### 场景3：后台任务/自动化

```python
import schedule
from chatbot_sdk import create_client

client = create_client("automation_bot", "secret")
client.initialize()

def generate_daily_report():
    """每日报告生成"""
    response = client.chat("""
    请执行以下任务：
    1. 查询昨天的销售数据
    2. 生成分析报告
    3. 发送邮件给 sales@company.com
    """)
    print(f"报告已生成: {response}")

# 每天早上8点执行
schedule.every().day.at("08:00").do(generate_daily_report)
```

### 场景4：桌面应用集成

```python
import tkinter as tk
from chatbot_sdk import create_client

class ChatApp:
    def __init__(self):
        self.client = create_client("desktop_app", "secret")
        self.client.initialize()
        
        self.root = tk.Tk()
        self.setup_ui()
    
    def send_message(self):
        message = self.input_box.get()
        
        # 流式显示响应
        for chunk in self.client.chat(message, stream=True):
            if chunk["type"] == "text":
                self.display_text(chunk["content"])
    
    def setup_ui(self):
        # UI设置...
        pass
```

## 📝 API参考

### ChatBotSDK

#### `__init__(config: ChatBotConfig)`
创建SDK实例。

#### `initialize() -> Dict`
初始化集成，注册配置。

**Returns:** 初始化结果

#### `chat(message: str, session_id: str = None, stream: bool = False, use_rag: bool = True, context: Dict = None)`
发送聊天消息。

**Parameters:**
- `message`: 用户消息（支持@路径引用）
- `session_id`: 会话ID（可选，用于保持上下文）
- `stream`: 是否流式输出
- `use_rag`: 是否使用RAG检索
- `context`: 额外上下文信息

**Returns:**
- 如果 `stream=False`: 返回完整响应字典
- 如果 `stream=True`: 返回Iterator[Dict]

#### `upload_document(content: str, filename: str, metadata: Dict = None) -> Dict`
上传文档到RAG知识库。

#### `upload_file(file_path: str, metadata: Dict = None) -> Dict`
从文件路径上传文档。

#### `register_tool(name: str, description: str, parameters: Dict, endpoint: str, auth: Dict = None) -> Dict`
注册自定义MCP工具。

#### `list_tools() -> Dict`
列出所有可用工具。

#### `health_check() -> Dict`
健康检查。

## 🔐 认证

SDK使用HMAC-SHA256签名认证：

```python
# 签名算法
signature = HMAC-SHA256(app_secret, app_id + timestamp + body)
```

请求头：
```
X-App-Id: your_app_id
X-Timestamp: 1234567890
X-Signature: computed_signature
```

## ⚙️ 配置选项

### ChatBotConfig

```python
@dataclass
class ChatBotConfig:
    app_id: str                      # 应用ID（必填）
    app_secret: str                  # 应用密钥（必填）
    base_url: str                    # 服务地址
    workspace_root: str              # 工作区根目录（@引用）
    mcp_servers: List[Dict]          # MCP服务器配置
    rag_config: Dict                 # RAG配置
    webhook_url: str                 # Webhook回调地址
    timeout: int                     # 请求超时时间（秒）
```

## 🐛 错误处理

```python
from chatbot_sdk import ChatBotSDK
import requests

try:
    client = ChatBotSDK(config)
    client.initialize()
    response = client.chat("Hello")
    
except requests.HTTPError as e:
    if e.response.status_code == 401:
        print("认证失败，请检查app_id和app_secret")
    elif e.response.status_code == 500:
        print("服务器错误")
    
except RuntimeError as e:
    print(f"SDK未初始化: {e}")
    
except Exception as e:
    print(f"未知错误: {e}")
```

## 📊 最佳实践

### 1. 连接管理

```python
# ✅ 推荐：复用客户端实例
client = create_client("app", "secret")
client.initialize()

# 多次调用
for message in messages:
    response = client.chat(message)

# ❌ 避免：每次都创建新实例
for message in messages:
    client = create_client("app", "secret")  # 浪费资源
    client.initialize()
    response = client.chat(message)
```

### 2. 会话管理

```python
# 为每个用户维护独立会话
user_sessions = {}

def chat_with_user(user_id: str, message: str):
    if user_id not in user_sessions:
        user_sessions[user_id] = f"session_{user_id}"
    
    return client.chat(
        message=message,
        session_id=user_sessions[user_id]
    )
```

### 3. 批量上传文档

```python
import os
from pathlib import Path

def upload_directory(directory: str):
    """批量上传目录下的所有文档"""
    for file_path in Path(directory).rglob("*.md"):
        try:
            client.upload_file(str(file_path), metadata={
                "source": "docs",
                "path": str(file_path.relative_to(directory))
            })
            print(f"✓ Uploaded: {file_path.name}")
        except Exception as e:
            print(f"✗ Failed: {file_path.name} - {e}")

upload_directory("./knowledge_base")
```

## 🔗 相关链接

- [完整文档](../../docs/README.md)
- [集成指南](../../docs/INTEGRATION_GUIDE.md)
- [示例代码](../../examples/sdk_integration_examples.py)
- [API文档](http://localhost:8000/docs)

## 💬 支持

- Issues: [GitHub Issues](https://github.com/your-org/agentic_chatBot/issues)
- 文档: [完整文档](../../docs/)
- 示例: [集成示例](../../examples/)

## 📄 License

MIT License

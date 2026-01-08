# Agentic ChatBot SDK

轻量级 Python SDK，通过 REST API 与 Agentic ChatBot 后端服务通信。

## 安装

```bash
pip install -e ./agentic_sdk
```

## 快速开始

### 1. 启动后端服务

```bash
cd backend && python run.py
```

### 2. 使用 SDK

```python
from agentic_sdk import ChatBot

# 创建客户端
bot = ChatBot(base_url="http://localhost:8000")

# 对话
response = bot.chat("你好")
print(response.text)

# 流式对话
for chunk in bot.chat_stream("讲个故事"):
    print(chunk.content, end="", flush=True)
```

## API 参考

### 初始化

```python
from agentic_sdk import ChatBot

# 基础用法
bot = ChatBot(base_url="http://localhost:8000")

# 带认证
bot = ChatBot(
    base_url="http://localhost:8000",
    api_key="your-api-key",
    timeout=60,  # 超时时间（秒）
)

# 使用 context manager
with ChatBot(base_url="http://localhost:8000") as bot:
    response = bot.chat("你好")
```

### 对话 API

```python
# 同步对话
response = bot.chat("你好", session_id="user-123")
print(response.text)
print(response.sources)  # RAG 来源
print(response.used_tools)  # 使用的工具

# 流式对话
for chunk in bot.chat_stream("讲个故事"):
    if chunk.type == "text":
        print(chunk.content, end="")
    elif chunk.type == "tool_call":
        print(f"调用工具: {chunk.metadata}")

# 意图分析
intent = bot.analyze_intent("帮我写一个 Python 函数")
print(intent.task_type)  # "code_generation"
print(intent.suggested_tools)

# 提交反馈
bot.submit_feedback(session_id="user-123", feedback="positive")

# 清除会话
bot.clear_session(session_id="user-123")

# 批量对话
responses = bot.chat_batch(
    messages=["你好", "天气怎么样?", "讲个笑话"],
    parallel=True,
)
```

### 文档 API

```python
# 搜索文档
results = bot.search_documents("如何配置?", top_k=5)

# 列出文档
docs = bot.list_documents(page=1, page_size=20)

# 获取文档详情
doc = bot.get_document(document_id="doc-123")

# 删除文档
bot.delete_document(document_id="doc-123")
```

### 设置 API

```python
# 索引管理
status = bot.get_index_status(workspace="/path/to/project")
bot.sync_index(force=True, workspace="/path/to/project")
bot.clear_index(workspace="/path/to/project")

# 规则管理
rules = bot.get_rules()
bot.add_rule("始终使用中文回答", rule_type="user")
bot.remove_rule("始终使用中文回答", rule_type="user")

# 技能管理
skills = bot.list_skills()
skill = bot.get_skill(skill_id="code_assistant")
bot.toggle_skill(skill_id="code_assistant", enabled=True)
bot.create_skill(
    skill_id="my_skill",
    name="我的技能",
    description="自定义技能",
    instructions="...",
    triggers=["关键词1", "关键词2"],
)
bot.update_skill(skill_id="my_skill", enabled=False)
bot.delete_skill(skill_id="my_skill")

# MCP 服务器管理
servers = bot.list_mcp_servers()
bot.add_mcp_server(name="my-mcp", server_type="stdio", url=None)
bot.remove_mcp_server(name="my-mcp")

# 获取设置摘要
summary = bot.get_settings_summary(workspace="/path/to/project")
```

### 系统 API

```python
# 健康检查
health = bot.health_check()

# 统计信息
stats = bot.get_stats()
```

## 响应类型

### ChatResponse

```python
@dataclass
class ChatResponse:
    text: str           # 响应文本
    session_id: str     # 会话 ID
    used_tools: List[str]  # 使用的工具
    sources: List[Dict]    # RAG 来源
    duration_ms: int       # 处理时间
    intent: Optional[str]  # 意图
```

### ChatChunk（流式响应）

```python
@dataclass
class ChatChunk:
    type: str      # text, tool_call, tool_result, complete, error
    content: str   # 内容
    metadata: Dict # 元数据
```

### IntentResult

```python
@dataclass
class IntentResult:
    surface_intent: str      # 表面意图
    deep_intent: str         # 深层意图
    task_type: str           # 任务类型
    complexity: str          # 复杂度
    is_multi_step: bool      # 是否多步骤
    suggested_tools: List[str]  # 建议工具
    confidence: float        # 置信度
```

## 异常处理

```python
from agentic_sdk import (
    ChatBot,
    ConnectionError,
    AuthenticationError,
    APIError,
)

try:
    bot = ChatBot(base_url="http://localhost:8000")
    response = bot.chat("你好")
except ConnectionError as e:
    print(f"无法连接到后端: {e}")
except AuthenticationError as e:
    print(f"认证失败: {e}")
except APIError as e:
    print(f"API 错误: {e}")
```

## 集成示例

### Flask 应用

```python
from flask import Flask, request, jsonify
from agentic_sdk import ChatBot

app = Flask(__name__)
bot = ChatBot(base_url="http://localhost:8000")

@app.route("/chat", methods=["POST"])
def chat():
    message = request.json.get("message")
    session_id = request.json.get("session_id", "default")
    
    response = bot.chat(message, session_id=session_id)
    
    return jsonify({
        "text": response.text,
        "sources": response.sources,
    })
```

### FastAPI 应用

```python
from fastapi import FastAPI
from pydantic import BaseModel
from agentic_sdk import ChatBot

app = FastAPI()
bot = ChatBot(base_url="http://localhost:8000")

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

@app.post("/chat")
async def chat(req: ChatRequest):
    response = bot.chat(req.message, session_id=req.session_id)
    return {"text": response.text, "sources": response.sources}
```

### Streamlit 应用

```python
import streamlit as st
from agentic_sdk import ChatBot

bot = ChatBot(base_url="http://localhost:8000")

st.title("AI 助手")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("输入消息"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.write(prompt)
    
    with st.chat_message("assistant"):
        response = bot.chat(prompt)
        st.write(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
```

## 版本历史

- **v0.3.0** - 简化 SDK，移除嵌入模式，专注于 REST API 调用
- **v0.2.0** - 支持远程模式和嵌入模式
- **v0.1.0** - 初始版本

# ⚡ 集成示例 - 5 分钟上手

本目录包含各种集成示例，展示如何用**最简单的方式**将 Agentic ChatBot 集成到你的应用中。

## 🎯 推荐学习路径

### 1️⃣ **新手必看** - 3 行代码集成 ⭐⭐⭐⭐⭐
```bash
python quick_integration.py
```
**学习时间**: 5 分钟  
**内容**: 最简单的集成方式，包含 @路径引用、流式输出、工具调用等核心功能

### 2️⃣ **框架集成** - 实际项目集成 ⭐⭐⭐⭐⭐
```bash
python framework_integrations.py
```
**学习时间**: 10 分钟  
**内容**: Flask、Django、FastAPI、Express.js、React 等主流框架的集成代码

### 3️⃣ **完整示例** - 深入理解 ⭐⭐⭐⭐
```bash
python sdk_integration_examples.py
```
**学习时间**: 20 分钟  
**内容**: SDK 所有功能的完整演示

## 📂 目录结构

```
examples/
├── quick_integration.py         # ⭐ 3 行代码极简集成（推荐）
├── framework_integrations.py    # ⭐ 常见框架集成代码（推荐）
├── sdk_integration_examples.py  # SDK 完整功能示例
├── desktop_app_integration.py   # 桌面应用集成示例
└── mcp_servers/                 # MCP 服务器示例
    └── database_tools/          # 数据库工具 MCP 服务器
```

## 🚀 最简单的示例（3 行代码）

```python
from chatbot_sdk import ChatBot

bot = ChatBot(base_url="http://localhost:8000")
response = bot.chat("@src/user.py 这个文件有什么问题？")
```

就这么简单！查看 `quick_integration.py` 了解更多。

## 🔌 框架集成示例

### Flask 应用

```python
from flask import Flask, request, jsonify
from chatbot_sdk import ChatBot

app = Flask(__name__)
bot = ChatBot(base_url="http://localhost:8000")

@app.route('/api/chat', methods=['POST'])
def chat():
    message = request.json.get('message')
    response = bot.chat(message)
    return jsonify({'response': response})
```

### FastAPI 应用

```python
from fastapi import FastAPI
from chatbot_sdk import ChatBot

app = FastAPI()
bot = ChatBot(base_url="http://localhost:8000")

@app.post("/api/chat")
async def chat(message: str):
    response = bot.chat(message)
    return {"response": response}
```

查看 `framework_integrations.py` 了解更多框架集成示例。

## 📚 SDK 完整功能

查看 `sdk_integration_examples.py` 了解：
- RAG 知识库集成
- 工具调用
- 会话管理
- 流式输出
- 错误处理

## 🖥️ 桌面应用集成

查看 `desktop_app_integration.py` 了解如何将 ChatBot 嵌入到 PyQt/Tkinter 桌面应用。

## 🔧 MCP 服务器示例

### 数据库工具服务器

提供 SQLite 数据库查询能力的 MCP 服务器：

```bash
cd mcp_servers/database_tools
pip install -r requirements.txt
python server.py
```

详见 [mcp_servers/database_tools/README.md](./mcp_servers/database_tools/README.md)

## 运行示例

```bash
# 确保后端服务正在运行
cd ../backend
source activate.csh
python run.py

# 在另一个终端运行示例
cd ../examples
python sdk_integration_examples.py
```

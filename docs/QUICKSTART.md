# 🚀 5 分钟快速开始

**目标**: 5 分钟内给你的应用加上 Cursor 级别的 AI 助手

---

## 📦 方式一：一键安装（推荐）

```bash
# 克隆项目
git clone https://github.com/xpc123/agenic_chatBot.git
cd agenic_chatBot

# 一键安装（自动完成所有配置）
chmod +x quick_install.sh
./quick_install.sh

# 或使用 csh 版本
chmod +x quick_install.csh
./quick_install.csh
```

安装脚本会自动：
- ✅ 创建虚拟环境
- ✅ 安装所有依赖
- ✅ 创建配置文件
- ✅ 创建数据目录

**唯一需要手动做的**：编辑 `backend/.env`，填入你的 `OPENAI_API_KEY`

---

## 🎯 方式二：3 行代码集成

### 1. 启动后端服务

```bash
cd backend
source venv/bin/activate  # 或 activate.csh
python run.py
```

服务启动在 `http://localhost:8000`

### 2. 在你的应用中集成（3 行代码）

```python
from chatbot_sdk import ChatBot

bot = ChatBot(base_url="http://localhost:8000")
response = bot.chat("帮我分析 @src/user.py 这个文件")
```

**就这么简单！**你的应用现在已经有了 Cursor 级别的 AI 助手 🎉

---

## 💡 核心功能演示

### 1️⃣ @路径引用（类似 Cursor）

```python
# 引用文件进行分析
response = bot.chat("@src/models/user.py 这个类有什么问题？")

# 引用多个文件
response = bot.chat("""
@src/api/auth.py 和 @src/models/user.py 
这两个文件如何协同工作？
""")
```

### 2️⃣ RAG 知识库

```python
# 上传产品文档
bot.upload_document("./docs/product_spec.pdf")

# 基于文档回答
response = bot.chat("我们产品的核心功能是什么？", use_rag=True)
```

### 3️⃣ 工具调用

```python
# AI 会自动调用工具
response = bot.chat("帮我查询数据库中的用户数量")
# AI 会自动调用 database 工具

response = bot.chat("发送邮件给 admin@example.com")
# AI 会自动调用 email 工具
```

### 4️⃣ 流式输出

```python
# 实时流式响应
for chunk in bot.chat_stream("写一个 Python Web 服务"):
    print(chunk, end="", flush=True)
```

---

## 🔌 常见框架集成示例

### Flask 应用

```python
from flask import Flask, request, jsonify
from chatbot_sdk import ChatBot

app = Flask(__name__)
bot = ChatBot(base_url="http://localhost:8000")

@app.route('/api/assistant', methods=['POST'])
def assistant():
    message = request.json.get('message')
    response = bot.chat(message)
    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(port=5000)
```

### Django 应用

```python
# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from chatbot_sdk import ChatBot
import json

bot = ChatBot(base_url="http://localhost:8000")

@csrf_exempt
def assistant_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        message = data.get('message')
        response = bot.chat(message)
        return JsonResponse({'response': response})
```

### FastAPI 应用

```python
from fastapi import FastAPI
from pydantic import BaseModel
from chatbot_sdk import ChatBot

app = FastAPI()
bot = ChatBot(base_url="http://localhost:8000")

class Query(BaseModel):
    message: str

@app.post("/api/assistant")
async def assistant(query: Query):
    response = bot.chat(query.message)
    return {"response": response}
```

### Express.js (Node.js)

```javascript
const express = require('express');
const axios = require('axios');

const app = express();
app.use(express.json());

app.post('/api/assistant', async (req, res) => {
    const { message } = req.body;
    
    const response = await axios.post('http://localhost:8000/api/v1/chat/message', {
        message: message,
        session_id: req.session.id
    });
    
    res.json({ response: response.data.message });
});

app.listen(3000);
```

---

## 🎨 前端集成（React 示例）

```tsx
import { useState } from 'react';

function AIChatBot() {
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
            <input 
                value={message} 
                onChange={(e) => setMessage(e.target.value)}
                placeholder="问我任何问题..."
            />
            <button onClick={sendMessage}>发送</button>
            <div>{response}</div>
        </div>
    );
}
```

---

## 🔧 高级配置

### 自定义工具

```python
from chatbot_sdk import ChatBot

bot = ChatBot(
    base_url="http://localhost:8000",
    tools={
        "database": {
            "type": "mcp",
            "config": "./mcp_servers/database_tools/server.py"
        },
        "email": {
            "type": "mcp", 
            "config": "./mcp_servers/email_tools/server.py"
        }
    }
)
```

### 自定义 RAG 配置

```python
bot = ChatBot(
    base_url="http://localhost:8000",
    rag_config={
        "chunk_size": 500,
        "chunk_overlap": 50,
        "top_k": 5,
        "score_threshold": 0.7
    }
)
```

### 自定义上下文路径

```python
bot = ChatBot(
    base_url="http://localhost:8000",
    context_config={
        "workspace_root": "/path/to/your/project",
        "path_whitelist": [
            "**/*.py",
            "**/*.js",
            "docs/**/*.md",
            "config/**"
        ],
        "max_file_size": 1024 * 1024  # 1MB
    }
)
```

---

## ⏱️ 完整时间线

| 步骤 | 时间 | 操作 |
|-----|------|-----|
| 1. 安装 | ~2 分钟 | 运行 `quick_install.sh` |
| 2. 配置 | ~30 秒 | 填入 API Key |
| 3. 启动 | ~30 秒 | `python run.py` |
| 4. 集成 | ~1 分钟 | 3 行代码集成到应用 |
| 5. 测试 | ~1 分钟 | 发送测试消息 |
| **总计** | **~5 分钟** | **完成！** |

---

## 🎯 下一步

- 📖 查看完整文档：[docs/README.md](./README.md)
- 🔧 配置 MCP 工具：[docs/mcp_setup.md](./mcp_setup.md)
- 💡 更多示例：[examples/](../examples/)
- 🚀 生产部署：[docs/DEPLOYMENT.md](./DEPLOYMENT.md)

---

## ❓ 常见问题

### Q: 支持哪些 LLM？
A: OpenAI (GPT-4o/GPT-4o-mini)、Anthropic (Claude)、本地模型（通过兼容接口）

### Q: 可以离线运行吗？
A: 可以，使用本地模型（如 Ollama）替换 OpenAI

### Q: 如何部署到生产环境？
A: 参考 [DEPLOYMENT.md](./DEPLOYMENT.md)，支持 Docker、K8s 等

### Q: 支持多语言吗？
A: 目前提供 Python SDK，JavaScript/TypeScript SDK 开发中

### Q: 需要 GPU 吗？
A: 不需要，后端是轻量级的，RAG 使用 CPU 即可

---

## 🆘 需要帮助？

- 📧 提交 Issue: [GitHub Issues](https://github.com/xpc123/agenic_chatBot/issues)
- 💬 加入讨论: [Discussions](https://github.com/xpc123/agenic_chatBot/discussions)
- 📖 查看文档: [完整文档](./README.md)

---

**开始你的 AI 助手之旅吧！🚀**

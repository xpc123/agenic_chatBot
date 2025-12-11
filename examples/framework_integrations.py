"""
🔌 常见框架集成示例

演示如何将 Agentic ChatBot 集成到主流 Web 框架
"""

# ============================================
# Flask 集成
# ============================================

FLASK_EXAMPLE = '''
# ========== Flask 集成示例 ==========
# 文件: app.py

from flask import Flask, request, jsonify, Response
from chatbot_sdk import ChatBot
import json

app = Flask(__name__)

# 初始化 ChatBot
bot = ChatBot(base_url="http://localhost:8000")

# 基础聊天接口
@app.route('/api/chat', methods=['POST'])
def chat():
    """基础聊天接口"""
    data = request.json
    message = data.get('message')
    use_rag = data.get('use_rag', False)
    
    response = bot.chat(message, use_rag=use_rag)
    return jsonify({
        'success': True,
        'response': response
    })

# 流式聊天接口
@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """流式聊天接口"""
    data = request.json
    message = data.get('message')
    
    def generate():
        for chunk in bot.chat_stream(message):
            yield f"data: {json.dumps({'chunk': chunk})}\\n\\n"
    
    return Response(generate(), mimetype='text/event-stream')

# 上传文档到 RAG
@app.route('/api/documents/upload', methods=['POST'])
def upload_document():
    """上传文档"""
    file = request.files.get('file')
    if file:
        # 保存文件
        filepath = f"./uploads/{file.filename}"
        file.save(filepath)
        
        # 添加到 RAG
        bot.upload_document(filepath)
        return jsonify({'success': True, 'message': 'Document uploaded'})
    
    return jsonify({'success': False, 'message': 'No file provided'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

# ========== 使用方法 ==========
# 1. pip install flask chatbot-sdk
# 2. python app.py
# 3. 测试: curl -X POST http://localhost:5000/api/chat \\
#          -H "Content-Type: application/json" \\
#          -d '{"message": "你好"}'
'''

# ============================================
# Django 集成
# ============================================

DJANGO_EXAMPLE = '''
# ========== Django 集成示例 ==========
# 文件: chatbot/views.py

from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from chatbot_sdk import ChatBot
import json

# 全局初始化
bot = ChatBot(base_url="http://localhost:8000")

@csrf_exempt
@require_http_methods(["POST"])
def chat_view(request):
    """聊天视图"""
    try:
        data = json.loads(request.body)
        message = data.get('message')
        use_rag = data.get('use_rag', False)
        
        response = bot.chat(message, use_rag=use_rag)
        
        return JsonResponse({
            'success': True,
            'response': response
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def chat_stream_view(request):
    """流式聊天视图"""
    try:
        data = json.loads(request.body)
        message = data.get('message')
        
        def event_stream():
            for chunk in bot.chat_stream(message):
                yield f"data: {json.dumps({'chunk': chunk})}\\n\\n"
        
        return StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# ========== urls.py ==========
from django.urls import path
from . import views

urlpatterns = [
    path('api/chat/', views.chat_view, name='chat'),
    path('api/chat/stream/', views.chat_stream_view, name='chat_stream'),
]

# ========== 使用方法 ==========
# 1. pip install django chatbot-sdk
# 2. 添加路由到项目 urls.py
# 3. python manage.py runserver
'''

# ============================================
# FastAPI 集成
# ============================================

FASTAPI_EXAMPLE = '''
# ========== FastAPI 集成示例 ==========
# 文件: main.py

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from chatbot_sdk import ChatBot
import json

app = FastAPI(title="AI Assistant API")

# 初始化 ChatBot
bot = ChatBot(base_url="http://localhost:8000")

class ChatRequest(BaseModel):
    message: str
    use_rag: bool = False
    session_id: str | None = None

class ChatResponse(BaseModel):
    success: bool
    response: str

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """基础聊天接口"""
    try:
        response = bot.chat(
            message=request.message,
            use_rag=request.use_rag,
            session_id=request.session_id
        )
        return ChatResponse(success=True, response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式聊天接口"""
    async def generate():
        try:
            for chunk in bot.chat_stream(request.message):
                yield f"data: {json.dumps({'chunk': chunk})}\\n\\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\\n\\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """上传文档"""
    try:
        # 保存文件
        filepath = f"./uploads/{file.filename}"
        with open(filepath, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 添加到 RAG
        bot.upload_document(filepath)
        return {"success": True, "message": "Document uploaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}

# ========== 使用方法 ==========
# 1. pip install fastapi uvicorn chatbot-sdk
# 2. uvicorn main:app --reload
# 3. 访问: http://localhost:8000/docs
'''

# ============================================
# Express.js 集成 (Node.js)
# ============================================

EXPRESS_EXAMPLE = '''
// ========== Express.js 集成示例 ==========
// 文件: app.js

const express = require('express');
const axios = require('axios');
const multer = require('multer');
const FormData = require('form-data');

const app = express();
app.use(express.json());

// ChatBot 配置
const CHATBOT_BASE_URL = 'http://localhost:8000';

// 基础聊天接口
app.post('/api/chat', async (req, res) => {
    try {
        const { message, use_rag = false, session_id } = req.body;
        
        const response = await axios.post(
            `${CHATBOT_BASE_URL}/api/v1/chat/message`,
            {
                message,
                use_rag,
                session_id
            }
        );
        
        res.json({
            success: true,
            response: response.data.message
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// 流式聊天接口
app.post('/api/chat/stream', async (req, res) => {
    try {
        const { message } = req.body;
        
        const response = await axios.post(
            `${CHATBOT_BASE_URL}/api/v1/chat/message`,
            { message, stream: true },
            { responseType: 'stream' }
        );
        
        res.setHeader('Content-Type', 'text/event-stream');
        response.data.pipe(res);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// 文档上传
const upload = multer({ dest: 'uploads/' });

app.post('/api/documents/upload', upload.single('file'), async (req, res) => {
    try {
        const formData = new FormData();
        formData.append('file', req.file.buffer, req.file.originalname);
        
        await axios.post(
            `${CHATBOT_BASE_URL}/api/v1/documents/upload`,
            formData,
            { headers: formData.getHeaders() }
        );
        
        res.json({ success: true, message: 'Document uploaded' });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

const PORT = 3000;
app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});

// ========== 使用方法 ==========
// 1. npm install express axios multer form-data
// 2. node app.js
// 3. 测试: curl -X POST http://localhost:3000/api/chat \\
//          -H "Content-Type: application/json" \\
//          -d '{"message": "你好"}'
'''

# ============================================
# React 前端集成
# ============================================

REACT_EXAMPLE = '''
// ========== React 集成示例 ==========
// 文件: ChatBot.tsx

import React, { useState } from 'react';
import axios from 'axios';

interface Message {
    role: 'user' | 'assistant';
    content: string;
}

export function ChatBot() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);

    const sendMessage = async () => {
        if (!input.trim()) return;

        // 添加用户消息
        const userMessage: Message = { role: 'user', content: input };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setLoading(true);

        try {
            // 调用后端 API
            const response = await axios.post('/api/chat', {
                message: input
            });

            // 添加助手回复
            const assistantMessage: Message = {
                role: 'assistant',
                content: response.data.response
            };
            setMessages(prev => [...prev, assistantMessage]);
        } catch (error) {
            console.error('Error:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="chatbot-container">
            <div className="messages">
                {messages.map((msg, idx) => (
                    <div key={idx} className={`message ${msg.role}`}>
                        {msg.content}
                    </div>
                ))}
                {loading && <div className="loading">思考中...</div>}
            </div>
            
            <div className="input-area">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                    placeholder="问我任何问题..."
                />
                <button onClick={sendMessage}>发送</button>
            </div>
        </div>
    );
}

// ========== 使用方法 ==========
// 1. npm install axios
// 2. 在你的组件中导入: import { ChatBot } from './ChatBot';
// 3. 使用: <ChatBot />
'''

# ============================================
# 打印所有示例
# ============================================

def print_all_examples():
    """打印所有框架集成示例"""
    print("\n" + "=" * 80)
    print("🔌 常见框架集成示例")
    print("=" * 80)
    
    print("\n📦 1. Flask 集成")
    print(FLASK_EXAMPLE)
    
    print("\n📦 2. Django 集成")
    print(DJANGO_EXAMPLE)
    
    print("\n📦 3. FastAPI 集成")
    print(FASTAPI_EXAMPLE)
    
    print("\n📦 4. Express.js 集成 (Node.js)")
    print(EXPRESS_EXAMPLE)
    
    print("\n📦 5. React 前端集成")
    print(REACT_EXAMPLE)
    
    print("\n" + "=" * 80)
    print("✅ 所有示例已显示")
    print("=" * 80)
    print("\n💡 提示: 复制对应框架的代码到你的项目中即可")
    print("📖 更多信息: docs/QUICKSTART.md\n")

if __name__ == "__main__":
    print_all_examples()

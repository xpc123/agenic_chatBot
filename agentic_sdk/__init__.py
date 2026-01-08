# -*- coding: utf-8 -*-
"""
Agentic ChatBot SDK
===================

轻量级 SDK 客户端，通过 REST API 与后端服务通信。

使用前请确保后端服务已启动::

    cd backend && python run.py

快速开始::

    from agentic_sdk import ChatBot
    
    # 创建客户端（连接到后端服务）
    bot = ChatBot(base_url="http://localhost:8000")
    
    # 同步对话
    response = bot.chat("你好")
    print(response.text)
    
    # 流式对话
    for chunk in bot.chat_stream("讲个故事"):
        print(chunk.content, end="", flush=True)

带认证::

    bot = ChatBot(
        base_url="http://localhost:8000",
        api_key="your-api-key"
    )

文档搜索::

    # 搜索知识库
    results = bot.search_documents("如何使用?")
    
    # 列出文档
    docs = bot.list_documents()

技能管理::

    # 列出技能
    skills = bot.list_skills()
    
    # 启用/禁用技能
    bot.toggle_skill("code_assistant", enabled=True)
"""

__version__ = "0.3.0"
__author__ = "Agentic ChatBot Team"

from .client import ChatBot
from .types import (
    ChatResponse,
    ChatChunk,
    IntentResult,
    ToolCall,
    MessageRole,
    Message,
    Conversation,
)
from .exceptions import (
    AgenticSDKError,
    ConnectionError,
    AuthenticationError,
    APIError,
    ValidationError,
    TimeoutError,
)

__all__ = [
    # 核心客户端
    "ChatBot",
    # 响应类型
    "ChatResponse",
    "ChatChunk",
    "IntentResult",
    # 对话类型
    "ToolCall",
    "MessageRole",
    "Message",
    "Conversation",
    # 异常
    "AgenticSDKError",
    "ConnectionError",
    "AuthenticationError",
    "APIError",
    "ValidationError",
    "TimeoutError",
]

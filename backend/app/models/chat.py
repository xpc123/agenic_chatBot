# -*- coding: utf-8 -*-
"""
聊天相关数据模型
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """聊天消息"""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    session_id: Optional[str] = None
    stream: bool = True
    use_rag: bool = True
    use_planning: bool = True
    context: Optional[Dict[str, Any]] = None
    

class ChatResponse(BaseModel):
    """聊天响应"""
    message: str
    session_id: str
    thoughts: Optional[str] = None  # Agent的思考过程
    tool_calls: Optional[List[Dict[str, Any]]] = None
    sources: Optional[List[Dict[str, Any]]] = None  # RAG引用来源
    metadata: Optional[Dict[str, Any]] = None
    

class StreamChunk(BaseModel):
    """流式响应块"""
    type: str  # text, thought, tool_call, source
    content: str
    metadata: Optional[Dict[str, Any]] = None
    

class ConversationHistory(BaseModel):
    """对话历史"""
    session_id: str
    messages: List[ChatMessage]
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None

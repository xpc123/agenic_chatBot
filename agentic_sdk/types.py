# -*- coding: utf-8 -*-
"""
SDK 类型定义
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class MessageRole(Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class ToolCall:
    """
    工具调用信息
    """
    id: str
    name: str
    arguments: Dict[str, Any]
    result: Optional[str] = None
    success: bool = True
    error: Optional[str] = None
    duration_ms: int = 0


@dataclass
class ChatResponse:
    """
    对话响应
    
    Attributes:
        text: 响应文本
        tool_calls: 工具调用列表
        sources: RAG 来源引用
        session_id: 会话 ID
        metadata: 额外元数据
    """
    text: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    session_id: str = ""
    
    # 性能指标
    latency_ms: int = 0
    token_count: int = 0
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def has_tool_calls(self) -> bool:
        """是否包含工具调用"""
        return len(self.tool_calls) > 0
    
    @property
    def has_sources(self) -> bool:
        """是否包含知识库引用"""
        return len(self.sources) > 0


@dataclass
class ChatChunk:
    """
    流式响应块
    
    用于流式对话时的增量输出
    """
    type: str  # text, tool_call, tool_result, thinking, progress, error, complete
    content: str = ""
    
    # 工具调用相关
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[str] = None
    
    # 进度相关
    step: Optional[int] = None
    total_steps: Optional[int] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_text(self) -> bool:
        return self.type == "text"
    
    @property
    def is_complete(self) -> bool:
        return self.type == "complete"
    
    @property
    def is_error(self) -> bool:
        return self.type == "error"


@dataclass
class Message:
    """
    对话消息
    """
    role: MessageRole
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value,
            "content": self.content,
        }


@dataclass
class Conversation:
    """
    对话历史
    """
    session_id: str
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_message(self, role: MessageRole, content: str) -> Message:
        """添加消息"""
        msg = Message(role=role, content=content)
        self.messages.append(msg)
        self.updated_at = datetime.now()
        return msg
    
    def to_list(self) -> List[Dict[str, str]]:
        """转换为列表格式"""
        return [m.to_dict() for m in self.messages]
    
    @property
    def message_count(self) -> int:
        return len(self.messages)


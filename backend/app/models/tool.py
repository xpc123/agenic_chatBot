# -*- coding: utf-8 -*-
"""
工具相关数据模型
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class Tool(BaseModel):
    """工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema格式
    server_name: str  # 所属MCP Server
    enabled: bool = True
    metadata: Optional[Dict[str, Any]] = None
    

class ToolCall(BaseModel):
    """工具调用"""
    id: str
    tool_name: str
    arguments: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    

class ToolResult(BaseModel):
    """工具执行结果"""
    tool_call_id: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: float
    metadata: Optional[Dict[str, Any]] = None
    

class MCPServer(BaseModel):
    """MCP服务器"""
    name: str
    url: str
    description: Optional[str] = None
    enabled: bool = True
    auth: Optional[Dict[str, str]] = None  # 认证信息
    tools: List[Tool] = []
    health_check_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    

class MCPServerStatus(BaseModel):
    """MCP服务器状态"""
    name: str
    status: str  # online, offline, error
    tool_count: int
    last_check: datetime = Field(default_factory=datetime.now)
    error_message: Optional[str] = None

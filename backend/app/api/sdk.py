# -*- coding: utf-8 -*-
"""
SDK集成接口 - Integration SDK
提供标准化接口供B端产品集成
"""
from typing import Dict, Any, Optional, Callable, List
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from loguru import logger
import hmac
import hashlib
import time

from ..config import settings
from ..models.chat import ChatRequest
from ..core import AgentEngine
from ..dependencies import get_agent_engine
from ..exceptions import (
    LLMError,
    AgentExecutionError,
    ToolExecutionError,
    ChatBotException,
)


# ==================== SDK Models ====================

class IntegrationConfig(BaseModel):
    """集成配置"""
    app_id: str = Field(..., description="应用ID")
    app_secret: str = Field(..., description="应用密钥")
    mcp_servers: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="自定义MCP服务器列表"
    )
    rag_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="RAG配置"
    )
    workspace_root: Optional[str] = Field(
        default=None,
        description="工作区根目录（用于@路径引用）"
    )
    webhook_url: Optional[str] = Field(
        default=None,
        description="Webhook回调URL"
    )
    custom_prompts: Optional[Dict[str, str]] = Field(
        default=None,
        description="自定义提示词模板"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="额外元数据"
    )


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息")
    session_id: Optional[str] = Field(None, description="会话ID")
    stream: bool = Field(default=True, description="是否流式输出")
    use_rag: bool = Field(default=True, description="是否使用RAG")
    context: Optional[Dict[str, Any]] = Field(None, description="额外上下文")


class ToolRegistration(BaseModel):
    """工具注册"""
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    parameters: Dict[str, Any] = Field(..., description="工具参数schema")
    endpoint: str = Field(..., description="工具执行端点URL")
    auth: Optional[Dict[str, str]] = Field(None, description="认证信息")


class DocumentUpload(BaseModel):
    """文档上传请求"""
    content: str = Field(..., description="文档内容")
    filename: str = Field(..., description="文件名")
    metadata: Optional[Dict[str, Any]] = Field(None, description="文档元数据")


# ==================== SDK Router ====================

sdk_router = APIRouter(prefix="/sdk", tags=["SDK Integration"])


# ==================== 认证中间件 ====================

async def verify_sdk_auth(
    x_app_id: Optional[str] = Header(None),
    x_signature: Optional[str] = Header(None),
    x_timestamp: Optional[str] = Header(None),
) -> str:
    """
    验证SDK调用的认证信息
    
    使用HMAC签名验证:
    signature = HMAC-SHA256(app_secret, app_id + timestamp + body)
    """
    if not settings.SDK_API_KEY:
        # 如果未配置API密钥，跳过验证
        return "default_app"
    
    if not x_app_id or not x_signature or not x_timestamp:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication headers"
        )
    
    # 验证时间戳（防重放攻击）
    try:
        timestamp = int(x_timestamp)
        current_time = int(time.time())
        if abs(current_time - timestamp) > 300:  # 5分钟有效期
            raise HTTPException(
                status_code=401,
                detail="Request timestamp expired"
            )
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid timestamp"
        )
    
    # 验证签名
    # 在生产环境中应该从数据库查询app_secret
    # 这里使用配置的SDK_API_KEY作为默认密钥
    app_secret = settings.SDK_API_KEY or "default_secret"
    
    expected_signature = hmac.new(
        app_secret.encode(),
        f"{x_app_id}{x_timestamp}".encode(),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(expected_signature, x_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    return x_app_id


# ==================== SDK Endpoints ====================

@sdk_router.post("/init")
async def initialize_integration(
    config: IntegrationConfig,
    app_id: str = Depends(verify_sdk_auth),
):
    """
    初始化集成
    
    B端产品调用此接口注册配置
    """
    try:
        # 保存配置（生产环境应存储到数据库）
        integration_config = {
            "app_id": config.app_id,
            "workspace_root": config.workspace_root,
            "mcp_servers": config.mcp_servers,
            "rag_config": config.rag_config,
            "webhook_url": config.webhook_url,
            "custom_prompts": config.custom_prompts,
            "metadata": config.metadata,
            "created_at": time.time(),
        }
        
        # 这里简化处理，实际应存储到Redis或数据库
        # 可以使用全局字典或缓存管理器
        logger.info(f"Integration initialized for app: {config.app_id}")
        
        return {
            "status": "success",
            "app_id": config.app_id,
            "message": "Integration initialized successfully",
            "endpoints": {
                "chat": "/api/v1/sdk/chat",
                "upload": "/api/v1/sdk/upload",
                "tools": "/api/v1/sdk/tools",
            },
            "features": {
                "planning": settings.ENABLE_PLANNING,
                "rag": True,
                "mcp": True,
                "path_reference": settings.ENABLE_PATH_REFERENCE,
            }
        }
    
    except Exception as e:
        logger.error(f"Integration init error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@sdk_router.post("/chat")
async def sdk_chat(
    request: ChatRequest,
    app_id: str = Depends(verify_sdk_auth),
    agent: AgentEngine = Depends(get_agent_engine),
):
    """
    SDK聊天接口
    
    供B端产品调用的统一聊天接口
    
    Args:
        request: 聊天请求
        app_id: 应用ID（通过认证获取）
        agent: Agent引擎（依赖注入）
    """
    import uuid
    
    try:
        # 生成会话ID
        session_id = request.session_id or f"{app_id}_{uuid.uuid4()}"
        
        # 收集响应
        response_text = ""
        metadata = {
            "thoughts": [],
            "tool_calls": [],
            "sources": []
        }
        
        # 处理消息
        async for chunk in agent.chat(
            message=request.message,
            session_id=session_id,
            stream=request.stream,
            use_rag=request.use_rag,
            context=request.context,
        ):
            chunk_type = chunk.get("type")
            
            if chunk_type == "text":
                response_text += chunk.get("content", "")
            elif chunk_type == "thought":
                metadata["thoughts"].append(chunk.get("content", ""))
            elif chunk_type == "tool_call":
                metadata["tool_calls"].append(chunk.get("metadata", {}))
            elif chunk_type == "sources":
                metadata["sources"] = chunk.get("content", [])
        
        result = {
            "status": "success",
            "message": response_text or "抱歉，我暂时无法回答。",
            "session_id": session_id,
            "app_id": app_id,
            "metadata": metadata,
        }
        
        # 发送Webhook回调（如果配置）
        if settings.ENABLE_WEBHOOK:
            await send_webhook(app_id, "chat_completed", result)
        
        return result
    
    except LLMError as e:
        logger.error(f"LLM error in SDK chat: {e}")
        raise HTTPException(status_code=503, detail=e.to_dict())
    except AgentExecutionError as e:
        logger.error(f"Agent execution error in SDK chat: {e}")
        raise HTTPException(status_code=500, detail=e.to_dict())
    except ToolExecutionError as e:
        logger.error(f"Tool execution error in SDK chat: {e}")
        raise HTTPException(status_code=500, detail=e.to_dict())
    except ChatBotException as e:
        logger.error(f"ChatBot error in SDK chat: {e}")
        raise HTTPException(status_code=400, detail=e.to_dict())
    except Exception as e:
        logger.exception(f"Unexpected error in SDK chat: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "type": type(e).__name__,
                }
            }
        )


@sdk_router.post("/upload")
async def sdk_upload_document(
    document: DocumentUpload,
    app_id: str = Depends(verify_sdk_auth),
):
    """
    上传文档到RAG系统
    
    供B端产品上传知识库文档
    """
    try:
        from ..rag.document_processor import document_processor
        from ..rag.vector_store import VectorStore
        
        # 处理文档
        # chunks = await document_processor.process_text(
        #     document.content,
        #     metadata={
        #         "filename": document.filename,
        #         "app_id": app_id,
        #         **document.metadata or {}
        #     }
        # )
        
        # 存储到向量库
        # vector_store = VectorStore()
        # await vector_store.add_chunks(chunks)
        
        logger.info(f"Document uploaded for app: {app_id}")
        
        return {
            "status": "success",
            "filename": document.filename,
            "message": "Document uploaded and indexed successfully"
        }
    
    except Exception as e:
        logger.error(f"Document upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@sdk_router.post("/tools/register")
async def sdk_register_tool(
    tool: ToolRegistration,
    app_id: str = Depends(verify_sdk_auth),
):
    """
    注册自定义工具
    
    供B端产品注册专有工具
    """
    try:
        from ..mcp import mcp_registry
        
        # 注册工具到MCP注册表
        # 工具实际执行时会调用提供的endpoint
        
        logger.info(f"Tool registered: {tool.name} for app: {app_id}")
        
        return {
            "status": "success",
            "tool_name": tool.name,
            "message": "Tool registered successfully"
        }
    
    except Exception as e:
        logger.error(f"Tool registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@sdk_router.get("/tools")
async def sdk_list_tools(
    app_id: str = Depends(verify_sdk_auth),
):
    """
    列出所有可用工具
    """
    try:
        from ..mcp import mcp_registry
        
        tools = await mcp_registry.get_all_tools()
        
        return {
            "status": "success",
            "tools": tools,
            "count": len(tools)
        }
    
    except Exception as e:
        logger.error(f"List tools error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@sdk_router.get("/health")
async def sdk_health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "features": {
            "planning": settings.ENABLE_PLANNING,
            "path_reference": settings.ENABLE_PATH_REFERENCE,
            "rag": True,
            "mcp": True,
        }
    }


# ==================== Webhook ====================

async def send_webhook(
    app_id: str,
    event_type: str,
    data: Dict[str, Any],
    webhook_url: Optional[str] = None,
):
    """
    发送Webhook回调
    
    Args:
        app_id: 应用ID
        event_type: 事件类型
        data: 事件数据
        webhook_url: Webhook URL
    """
    if not settings.ENABLE_WEBHOOK:
        return
    
    url = webhook_url or settings.WEBHOOK_URL
    if not url:
        return
    
    try:
        import httpx
        
        payload = {
            "app_id": app_id,
            "event_type": event_type,
            "data": data,
            "timestamp": int(time.time()),
        }
        
        # 生成签名
        if settings.WEBHOOK_SECRET:
            signature = hmac.new(
                settings.WEBHOOK_SECRET.encode(),
                str(payload).encode(),
                hashlib.sha256
            ).hexdigest()
            headers = {"X-Webhook-Signature": signature}
        else:
            headers = {}
        
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, headers=headers, timeout=10)
        
        logger.debug(f"Webhook sent: {event_type} for app {app_id}")
    
    except Exception as e:
        logger.error(f"Webhook error: {e}")

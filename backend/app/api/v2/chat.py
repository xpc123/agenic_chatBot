# -*- coding: utf-8 -*-
"""
Chat API v2 - 聊天相关接口

端点:
- POST /chat/message     - 非流式对话
- POST /chat/stream      - 流式对话 (SSE)
- POST /chat/analyze-intent - 意图分析
- GET  /chat/preferences/{user_id} - 用户偏好
- POST /chat/feedback/{session_id} - 提交反馈
- GET  /chat/skills      - 技能列表
- GET  /chat/stats       - 系统统计
- DELETE /chat/session/{session_id} - 清除会话
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from loguru import logger
import json
import uuid
import asyncio

from ...core.cursor_style_orchestrator import CursorStyleOrchestrator
from ...core.intent_recognizer import get_intent_recognizer
from ...core.user_preferences import get_preference_manager
from ...core.skills import get_skills_manager
from ...llm import get_llm_client
from ...exceptions import ChatBotException
from ..middleware import get_current_user, AuthenticatedUser

router = APIRouter(prefix="/chat", tags=["chat-v2"])


# ==================== 请求/响应模型 ====================

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息")
    session_id: Optional[str] = Field(None, description="会话 ID")
    user_id: Optional[str] = Field(None, description="用户 ID")
    use_rag: bool = Field(True, description="是否使用 RAG")
    use_skills: bool = Field(True, description="是否使用 Skills")
    use_preferences: bool = Field(True, description="是否使用用户偏好")
    files: Optional[Dict[str, str]] = Field(None, description="引用的文件")
    context: Optional[Dict[str, Any]] = Field(None, description="额外上下文")


class ChatResponse(BaseModel):
    """聊天响应"""
    message: str = Field(..., description="AI 回复")
    session_id: str = Field(..., description="会话 ID")
    intent: Optional[Dict[str, Any]] = Field(None, description="识别的意图")
    used_tools: List[str] = Field(default_factory=list, description="使用的工具")
    execution_steps: int = Field(0, description="执行步骤数")
    duration_ms: int = Field(0, description="处理耗时(ms)")
    citations: List[Dict[str, str]] = Field(default_factory=list, description="引用来源")


class IntentAnalysisRequest(BaseModel):
    """意图分析请求"""
    message: str = Field(..., description="用户消息")


class IntentAnalysisResponse(BaseModel):
    """意图分析响应"""
    surface_intent: str
    deep_intent: str
    task_type: str
    complexity: str
    is_multi_step: bool
    required_capabilities: List[str]
    suggested_tools: List[str]
    confidence: float


class UserPreferenceResponse(BaseModel):
    """用户偏好响应"""
    user_id: str
    response_style: str
    language: str
    domains: List[str]
    favorite_tools: List[str]
    total_messages: int


# ==================== 全局编排器 ====================

_orchestrator: Optional[CursorStyleOrchestrator] = None


def get_chat_orchestrator() -> CursorStyleOrchestrator:
    """获取聊天编排器"""
    global _orchestrator
    
    if _orchestrator is None:
        try:
            llm_client = get_llm_client()
            
            from ...core.practical_tools import get_practical_tools
            tools = get_practical_tools()
            
            _orchestrator = CursorStyleOrchestrator(
                llm_client=llm_client,
                tools=tools,
                enable_rag=True,
                enable_skills=True,
                enable_memory=True,
                enable_preferences=True,
                max_context_tokens=8000,
            )
            
            logger.info("CursorStyleOrchestrator initialized for API v2")
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise HTTPException(
                status_code=503,
                detail={"error": "Service not ready", "message": str(e)}
            )
    
    return _orchestrator


# ==================== API 端点 ====================

@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    发送聊天消息 (非流式)
    """
    try:
        orchestrator = get_chat_orchestrator()
        
        session_id = request.session_id or str(uuid.uuid4())
        user_id = request.user_id or user.user_id or session_id
        
        response = await orchestrator.chat(
            message=request.message,
            session_id=session_id,
            user_id=user_id,
            files=request.files,
        )
        
        return ChatResponse(
            message=response.content or "抱歉，我暂时无法回答这个问题。",
            session_id=session_id,
            intent=response.intent.to_dict() if response.intent else None,
            used_tools=response.used_tools,
            execution_steps=response.execution_steps,
            duration_ms=response.duration_ms,
            citations=response.citations,
        )
        
    except ChatBotException as e:
        logger.error(f"ChatBot error: {e}")
        raise HTTPException(status_code=400, detail={"error": str(e)})
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.post("/stream")
async def stream_message(
    request: ChatRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    流式聊天消息 (SSE)
    """
    try:
        orchestrator = get_chat_orchestrator()
        
        session_id = request.session_id or str(uuid.uuid4())
        user_id = request.user_id or user.user_id or session_id
        
        async def generate_sse():
            try:
                async for chunk in orchestrator.chat_stream(
                    message=request.message,
                    session_id=session_id,
                    user_id=user_id,
                    files=request.files,
                ):
                    data = json.dumps(chunk.to_dict(), ensure_ascii=False)
                    yield f"data: {data}\n\n"
                    await asyncio.sleep(0.01)
                    
            except Exception as e:
                logger.error(f"SSE generation error: {e}")
                error_data = json.dumps({
                    "type": "error",
                    "content": str(e),
                }, ensure_ascii=False)
                yield f"data: {error_data}\n\n"
        
        return StreamingResponse(
            generate_sse(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
        
    except Exception as e:
        logger.exception(f"Stream error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Stream failed", "message": str(e)}
        )


@router.post("/analyze-intent", response_model=IntentAnalysisResponse)
async def analyze_intent(
    request: IntentAnalysisRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    分析用户意图
    """
    try:
        recognizer = get_intent_recognizer()
        
        intent = await recognizer.recognize(
            message=request.message,
            history=None,
            available_tools=None,
        )
        
        # 安全地获取 task_type（处理枚举或字符串）
        task_type = intent.task_type.value if hasattr(intent.task_type, 'value') else str(intent.task_type)
        
        # 安全地获取 required_capabilities（处理枚举列表或字符串列表）
        capabilities = []
        for c in intent.required_capabilities:
            capabilities.append(c.value if hasattr(c, 'value') else str(c))
        
        return IntentAnalysisResponse(
            surface_intent=intent.surface_intent,
            deep_intent=intent.deep_intent,
            task_type=task_type,
            complexity=intent.complexity,
            is_multi_step=intent.is_multi_step,
            required_capabilities=capabilities,
            suggested_tools=intent.suggested_tools,
            confidence=intent.confidence,
        )
        
    except Exception as e:
        logger.exception(f"Intent analysis error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Analysis failed", "message": str(e)}
        )


@router.get("/preferences/{user_id}", response_model=UserPreferenceResponse)
async def get_user_preferences(
    user_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    获取用户偏好
    """
    try:
        manager = get_preference_manager()
        summary = manager.get_user_summary(user_id)
        
        return UserPreferenceResponse(
            user_id=summary["user_id"],
            response_style=summary["response_style"],
            language=summary["language"],
            domains=summary["domains"],
            favorite_tools=summary["favorite_tools"],
            total_messages=summary["total_messages"],
        )
        
    except Exception as e:
        logger.exception(f"Get preferences error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to get preferences", "message": str(e)}
        )


@router.post("/feedback/{session_id}")
async def submit_feedback(
    session_id: str,
    feedback: str,
    user_id: Optional[str] = None,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    提交反馈
    """
    try:
        if feedback not in ["positive", "negative"]:
            raise HTTPException(
                status_code=400,
                detail={"error": "Invalid feedback. Use 'positive' or 'negative'"}
            )
        
        manager = get_preference_manager()
        user_id = user_id or user.user_id or session_id
        
        manager.learn_from_message(
            user_id=user_id,
            message="",
            response="",
            feedback=feedback,
        )
        
        return {"message": "Feedback recorded", "feedback": feedback}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Feedback error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to record feedback", "message": str(e)}
        )


@router.get("/skills")
async def list_skills(user: AuthenticatedUser = Depends(get_current_user)):
    """
    列出可用技能
    """
    try:
        manager = get_skills_manager()
        skills = manager.list_skills()
        
        return {
            "total": len(skills),
            "skills": [
                {
                    "id": skill.id,
                    "name": skill.name,
                    "description": skill.description,
                    "category": skill.category,
                    "triggers": skill.triggers,
                    "enabled": skill.enabled,
                }
                for skill in skills
            ]
        }
        
    except Exception as e:
        logger.exception(f"List skills error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to list skills", "message": str(e)}
        )


@router.get("/stats")
async def get_stats(user: AuthenticatedUser = Depends(get_current_user)):
    """
    获取系统统计
    """
    try:
        orchestrator = get_chat_orchestrator()
        stats = orchestrator.get_stats()
        
        return {
            "orchestrator": stats,
            "status": "healthy",
        }
        
    except Exception as e:
        return {
            "orchestrator": None,
            "status": "initializing",
            "error": str(e),
        }


@router.delete("/session/{session_id}")
async def clear_session(
    session_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    清除会话
    """
    try:
        orchestrator = get_chat_orchestrator()
        orchestrator.clear_session(session_id)
        
        return {"message": "Session cleared", "session_id": session_id}
        
    except Exception as e:
        logger.exception(f"Clear session error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to clear session", "message": str(e)}
        )


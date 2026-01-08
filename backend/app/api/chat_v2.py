# -*- coding: utf-8 -*-
"""
聊天 API v2 - 使用 Cursor 风格架构

新特性:
1. CursorStyleOrchestrator 编排器
2. SSE 流式响应
3. 意图识别展示
4. 进度追踪
5. 用户偏好学习
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from loguru import logger
import json
import uuid
import asyncio

from ..core.cursor_style_orchestrator import CursorStyleOrchestrator, get_orchestrator
from ..core.intent_recognizer import get_intent_recognizer
from ..core.user_preferences import get_preference_manager
from ..core.skills import get_skills_manager
from ..llm import get_llm_client
from ..exceptions import ChatBotException


router = APIRouter(prefix="/v2/chat", tags=["chat-v2"])


# ==================== 请求/响应模型 ====================

class ChatRequestV2(BaseModel):
    """聊天请求 V2"""
    message: str = Field(..., description="用户消息")
    session_id: Optional[str] = Field(None, description="会话 ID")
    user_id: Optional[str] = Field(None, description="用户 ID")
    
    # 功能开关
    use_rag: bool = Field(True, description="是否使用 RAG")
    use_skills: bool = Field(True, description="是否使用 Skills")
    use_preferences: bool = Field(True, description="是否使用用户偏好")
    
    # 额外上下文
    files: Optional[Dict[str, str]] = Field(None, description="引用的文件 {path: content}")
    context: Optional[Dict[str, Any]] = Field(None, description="额外上下文")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "帮我分析这个 Python 代码",
                "session_id": "user-123-session-1",
                "use_rag": True,
                "use_skills": True,
            }
        }


class ChatResponseV2(BaseModel):
    """聊天响应 V2"""
    message: str = Field(..., description="AI 回复")
    session_id: str = Field(..., description="会话 ID")
    
    # 意图信息
    intent: Optional[Dict[str, Any]] = Field(None, description="识别的意图")
    
    # 执行信息
    used_tools: List[str] = Field(default_factory=list, description="使用的工具")
    execution_steps: int = Field(0, description="执行步骤数")
    duration_ms: int = Field(0, description="处理耗时(ms)")
    
    # 引用来源
    citations: List[Dict[str, str]] = Field(default_factory=list, description="引用来源")


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
            
            # 导入实用工具
            from ..core.practical_tools import get_practical_tools
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
            
            logger.info("CursorStyleOrchestrator initialized for API")
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise HTTPException(
                status_code=503,
                detail={"error": "Service not ready", "message": str(e)}
            )
    
    return _orchestrator


# ==================== API 端点 ====================

@router.post("/message", response_model=ChatResponseV2)
async def send_message_v2(request: ChatRequestV2):
    """
    发送聊天消息 (非流式，使用新架构)
    
    使用 CursorStyleOrchestrator 处理消息，支持：
    - 深度意图识别
    - 智能工具编排
    - 用户偏好学习
    - RAG 知识检索
    """
    try:
        orchestrator = get_chat_orchestrator()
        
        session_id = request.session_id or str(uuid.uuid4())
        user_id = request.user_id or session_id
        
        # 调用编排器
        response = await orchestrator.chat(
            message=request.message,
            session_id=session_id,
            user_id=user_id,
            files=request.files,
        )
        
        return ChatResponseV2(
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
async def stream_message_v2(request: ChatRequestV2):
    """
    流式聊天消息 (SSE)
    
    使用 Server-Sent Events 实现流式响应，支持：
    - 实时思考过程展示
    - 工具调用进度
    - 逐字输出
    
    响应格式 (SSE):
    ```
    data: {"type": "thinking", "content": "分析您的请求..."}
    data: {"type": "tool_call", "content": "执行 shell_execute..."}
    data: {"type": "text", "content": "回答内容..."}
    data: {"type": "complete", "content": "", "metadata": {...}}
    ```
    """
    try:
        orchestrator = get_chat_orchestrator()
        
        session_id = request.session_id or str(uuid.uuid4())
        user_id = request.user_id or session_id
        
        async def generate_sse():
            """生成 SSE 流"""
            try:
                async for chunk in orchestrator.chat_stream(
                    message=request.message,
                    session_id=session_id,
                    user_id=user_id,
                    files=request.files,
                ):
                    # 格式化为 SSE
                    data = json.dumps(chunk.to_dict(), ensure_ascii=False)
                    yield f"data: {data}\n\n"
                    
                    # 小延迟以确保前端能正确处理
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
async def analyze_intent(request: ChatRequestV2):
    """
    分析用户意图
    
    仅进行意图分析，不执行实际操作。
    用于前端展示意图识别结果。
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
async def get_user_preferences(user_id: str):
    """
    获取用户偏好
    
    返回学习到的用户偏好信息。
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
    feedback: str,  # "positive" or "negative"
    user_id: Optional[str] = None,
):
    """
    提交反馈
    
    用于用户偏好学习。
    
    Args:
        session_id: 会话 ID
        feedback: "positive" 或 "negative"
        user_id: 用户 ID
    """
    try:
        if feedback not in ["positive", "negative"]:
            raise HTTPException(
                status_code=400,
                detail={"error": "Invalid feedback. Use 'positive' or 'negative'"}
            )
        
        manager = get_preference_manager()
        user_id = user_id or session_id
        
        # 记录反馈（这里简化处理，实际应该记录具体的消息）
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
async def list_skills():
    """
    列出可用技能
    
    返回所有已注册的 Skills。
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
async def get_stats():
    """
    获取系统统计
    
    返回编排器的统计信息。
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
async def clear_session(session_id: str):
    """
    清除会话
    
    清除指定会话的所有状态。
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


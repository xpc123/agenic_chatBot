"""
聊天API路由
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import StreamingResponse
from typing import Dict
from loguru import logger
import json
import uuid

from ..models.chat import ChatRequest, ChatResponse, StreamChunk
from ..core.agent import AgentEngine
from ..core.memory import MemoryManager
from ..dependencies import (
    get_agent_engine,
    get_memory_manager,
    get_tool_executor,
)
from ..exceptions import (
    ChatBotException,
    LLMError,
    AgentExecutionError,
    ToolExecutionError,
)
from ..mcp import mcp_registry
from ..rag import retriever

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    memory_manager: MemoryManager = Depends(get_memory_manager),
    agent: AgentEngine = Depends(get_agent_engine),
):
    """
    发送聊天消息 (非流式)
    
    Args:
        request: 聊天请求
        memory_manager: 内存管理器（依赖注入）
        agent: Agent引擎（依赖注入）
    
    Returns:
        聊天响应
    """
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        # 收集完整响应
        response_text = ""
        thoughts = []
        tool_calls = []
        sources = []
        
        # 处理消息并收集结果
        async for chunk in agent.chat(
            message=request.message,
            session_id=session_id,
            stream=False,
            use_rag=request.use_rag,
            context=request.context,
        ):
            chunk_type = chunk.get("type")
            
            if chunk_type == "text":
                response_text += chunk.get("content", "")
            elif chunk_type == "thought":
                thoughts.append(chunk.get("content", ""))
            elif chunk_type == "tool_call":
                tool_calls.append(chunk.get("metadata", {}))
            elif chunk_type == "sources":
                sources = chunk.get("content", [])
        
        return ChatResponse(
            message=response_text or "抱歉，我暂时无法回答这个问题。",
            session_id=session_id,
            thoughts="\n".join(thoughts) if thoughts else None,
            tool_calls=tool_calls if tool_calls else None,
            sources=sources if sources else None,
        )
        
    except LLMError as e:
        logger.error(f"LLM error: {e}")
        raise HTTPException(status_code=503, detail=e.to_dict())
    except AgentExecutionError as e:
        logger.error(f"Agent execution error: {e}")
        raise HTTPException(status_code=500, detail=e.to_dict())
    except ToolExecutionError as e:
        logger.error(f"Tool execution error: {e}")
        raise HTTPException(status_code=500, detail=e.to_dict())
    except ChatBotException as e:
        logger.error(f"ChatBot error: {e}")
        raise HTTPException(status_code=400, detail=e.to_dict())
    except Exception as e:
        logger.exception(f"Unexpected error in send_message: {e}")
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


@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket聊天接口 (流式)
    
    注意：WebSocket 不支持 Depends，所以手动获取依赖实例
    
    Args:
        websocket: WebSocket连接
        session_id: 会话ID
    """
    await websocket.accept()
    logger.info(f"WebSocket connected: {session_id}")
    
    # WebSocket 不支持 Depends，手动获取依赖实例
    # 每个连接复用单例组件，但创建新的 AgentEngine 实例
    agent = get_agent_engine()
    memory_manager = get_memory_manager()
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            user_message = message_data.get('message', '')
            use_rag = message_data.get('use_rag', True)
            use_planning = message_data.get('use_planning', True)
            context = message_data.get('context')
            
            logger.info(f"Processing message for session {session_id}: {user_message[:50]}...")
            
            # 流式处理消息
            try:
                async for chunk in agent.chat(
                    message=user_message,
                    session_id=session_id,
                    stream=True,
                    use_rag=use_rag,
                    context=context,
                ):
                    # 发送每个chunk到前端
                    await websocket.send_json(chunk)
                
                # 发送完成标记
                await websocket.send_json({
                    "type": "done",
                    "content": "",
                })
                
            except LLMError as e:
                logger.error(f"LLM error in WebSocket: {e}")
                await websocket.send_json({
                    "type": "error",
                    "content": f"LLM服务错误: {e.message}",
                })
            except AgentExecutionError as e:
                logger.error(f"Agent execution error in WebSocket: {e}")
                await websocket.send_json({
                    "type": "error",
                    "content": f"Agent执行错误: {e.message}",
                })
            except ToolExecutionError as e:
                logger.error(f"Tool execution error in WebSocket: {e}")
                await websocket.send_json({
                    "type": "error",
                    "content": f"工具执行错误: {e.message}",
                })
            except ChatBotException as e:
                logger.error(f"ChatBot error in WebSocket: {e}")
                await websocket.send_json({
                    "type": "error",
                    "content": f"处理错误: {e.message}",
                })
            except Exception as e:
                logger.exception(f"Unexpected error processing message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "content": "处理消息时发生未知错误",
                })
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass


@router.get("/history/{session_id}")
async def get_chat_history(
    session_id: str,
    memory_manager: MemoryManager = Depends(get_memory_manager),
):
    """
    获取聊天历史
    
    Args:
        session_id: 会话ID
        memory_manager: 内存管理器（依赖注入）
    
    Returns:
        聊天历史
    """
    try:
        history = await memory_manager.get_conversation_history(session_id)
        
        return {
            "session_id": session_id,
            "messages": [msg.model_dump() for msg in history],
        }
        
    except ChatBotException as e:
        logger.error(f"Get history error: {e}")
        raise HTTPException(status_code=400, detail=e.to_dict())
    except Exception as e:
        logger.exception(f"Unexpected error getting history: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "Failed to retrieve chat history",
                }
            }
        )


@router.delete("/history/{session_id}")
async def clear_chat_history(
    session_id: str,
    memory_manager: MemoryManager = Depends(get_memory_manager),
):
    """
    清除聊天历史
    
    Args:
        session_id: 会话ID
        memory_manager: 内存管理器（依赖注入）
    """
    try:
        await memory_manager.clear_session(session_id)
        
        return {"message": "History cleared successfully"}
        
    except ChatBotException as e:
        logger.error(f"Clear history error: {e}")
        raise HTTPException(status_code=400, detail=e.to_dict())
    except Exception as e:
        logger.exception(f"Unexpected error clearing history: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "Failed to clear chat history",
                }
            }
        )

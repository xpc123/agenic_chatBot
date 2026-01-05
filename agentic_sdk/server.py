# -*- coding: utf-8 -*-
"""
HTTP API 服务层

提供 RESTful API 和 SSE 流式接口，供非 Python 应用调用。

启动方式::

    # 方式 1: 命令行
    python -m agentic_sdk.server --host 0.0.0.0 --port 8000
    
    # 方式 2: 代码
    from agentic_sdk.server import create_app, run_server
    app = create_app()
    run_server(app, host="0.0.0.0", port=8000)
"""
import asyncio
import json
import uuid
from typing import Any, Dict, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from loguru import logger

from .chatbot import ChatBot
from .config import ChatConfig


# ==================== API Models ====================

class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., description="用户消息")
    session_id: Optional[str] = Field(None, description="会话 ID")
    stream: bool = Field(False, description="是否流式响应")


class ChatResponse(BaseModel):
    """对话响应"""
    text: str = Field(..., description="响应文本")
    session_id: str = Field(..., description="会话 ID")
    tool_calls: list = Field(default_factory=list, description="工具调用")
    sources: list = Field(default_factory=list, description="知识库来源")
    latency_ms: int = Field(0, description="响应延迟(ms)")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    timestamp: str


class ToolInfo(BaseModel):
    """工具信息"""
    name: str
    description: str
    category: str = "general"


class SkillInfo(BaseModel):
    """技能信息"""
    id: str
    name: str
    description: str
    category: str = "general"
    triggers: list = Field(default_factory=list)


# ==================== Server Class ====================

class ChatBotServer:
    """
    HTTP API 服务器
    
    封装 ChatBot SDK，提供 HTTP 接口。
    """
    
    def __init__(self, config: Optional[ChatConfig] = None):
        self.config = config or ChatConfig()
        self.bot = ChatBot(self.config)
        self.app = self._create_app()
    
    def _create_app(self) -> FastAPI:
        """创建 FastAPI 应用"""
        app = FastAPI(
            title="Agentic ChatBot API",
            description="通用 AI 助手 HTTP API",
            version="0.1.0",
            docs_url="/docs",
            redoc_url="/redoc",
        )
        
        # CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 注册路由
        self._register_routes(app)
        
        return app
    
    def _register_routes(self, app: FastAPI):
        """注册 API 路由"""
        
        # ===== 健康检查 =====
        
        @app.get("/health", response_model=HealthResponse, tags=["System"])
        async def health():
            """健康检查"""
            return HealthResponse(
                status="ok",
                version="0.1.0",
                timestamp=datetime.now().isoformat(),
            )
        
        # ===== 对话 API =====
        
        @app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
        async def chat(request: ChatRequest):
            """
            同步对话
            
            发送消息并获取完整响应。
            """
            try:
                response = await self.bot.chat_async(
                    message=request.message,
                    session_id=request.session_id,
                )
                
                return ChatResponse(
                    text=response.text,
                    session_id=response.session_id,
                    tool_calls=[tc.__dict__ for tc in response.tool_calls],
                    sources=response.sources,
                    latency_ms=response.latency_ms,
                )
            except Exception as e:
                logger.error(f"Chat error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/api/chat/stream", tags=["Chat"])
        async def chat_stream(request: ChatRequest):
            """
            流式对话 (SSE)
            
            发送消息并通过 Server-Sent Events 接收流式响应。
            
            响应格式::
            
                data: {"type": "text", "content": "你好"}
                data: {"type": "tool_call", "tool_name": "search", "tool_args": {...}}
                data: {"type": "complete", "content": ""}
            """
            async def generate():
                try:
                    async for chunk in self.bot.chat_stream_async(
                        message=request.message,
                        session_id=request.session_id,
                    ):
                        data = {
                            "type": chunk.type,
                            "content": chunk.content,
                        }
                        
                        if chunk.tool_name:
                            data["tool_name"] = chunk.tool_name
                        if chunk.tool_args:
                            data["tool_args"] = chunk.tool_args
                        if chunk.step is not None:
                            data["step"] = chunk.step
                            data["total_steps"] = chunk.total_steps
                        
                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                        
                except Exception as e:
                    logger.error(f"Stream error: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )
        
        # ===== 工具 API =====
        
        @app.get("/api/tools", response_model=list[ToolInfo], tags=["Tools"])
        async def list_tools():
            """列出所有可用工具"""
            tools = self.bot.list_tools()
            return [ToolInfo(**t) for t in tools]
        
        # ===== 技能 API =====
        
        @app.get("/api/skills", response_model=list[SkillInfo], tags=["Skills"])
        async def list_skills():
            """列出所有可用技能"""
            skills = self.bot.list_skills()
            return [SkillInfo(**s) for s in skills]
        
        # ===== 会话 API =====
        
        @app.get("/api/sessions", tags=["Session"])
        async def list_sessions():
            """列出所有会话"""
            return {"sessions": self.bot.list_sessions()}
        
        @app.delete("/api/sessions/{session_id}", tags=["Session"])
        async def clear_session(session_id: str):
            """清除会话历史"""
            self.bot.clear_conversation(session_id)
            return {"status": "ok", "session_id": session_id}
        
        # ===== 知识库 API =====
        
        @app.post("/api/knowledge/search", tags=["Knowledge"])
        async def search_knowledge(
            query: str = Query(..., description="搜索查询"),
            top_k: int = Query(5, description="返回数量"),
        ):
            """搜索知识库"""
            results = self.bot.search_knowledge(query, top_k=top_k)
            return {"query": query, "results": results}
    
    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """启动服务器"""
        import uvicorn
        
        logger.info(f"Starting server at http://{host}:{port}")
        logger.info(f"API docs: http://{host}:{port}/docs")
        
        uvicorn.run(self.app, host=host, port=port)


# ==================== 便捷函数 ====================

def create_app(config: Optional[ChatConfig] = None) -> FastAPI:
    """创建 FastAPI 应用"""
    server = ChatBotServer(config)
    return server.app


def run_server(
    app: Optional[FastAPI] = None,
    config: Optional[ChatConfig] = None,
    host: str = "0.0.0.0",
    port: int = 8000,
):
    """启动服务器"""
    import uvicorn
    
    if app is None:
        server = ChatBotServer(config)
        app = server.app
    
    uvicorn.run(app, host=host, port=port)


# ==================== CLI 入口 ====================

def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agentic ChatBot HTTP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    parser.add_argument("--config", help="Config file path")
    
    args = parser.parse_args()
    
    config = None
    if args.config:
        config = ChatConfig.from_file(args.config)
    
    server = ChatBotServer(config)
    server.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()


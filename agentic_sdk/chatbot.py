# -*- coding: utf-8 -*-
"""
ChatBot 主类 - SDK 核心
"""
import asyncio
import sys
import uuid
from typing import Any, Callable, Dict, Iterator, List, Optional, Union
from pathlib import Path
from functools import wraps
from datetime import datetime

from loguru import logger

from .config import ChatConfig
from .types import ChatResponse, ChatChunk, ToolCall, Message, Conversation, MessageRole


class ChatBot:
    """
    通用 AI 助手
    
    可嵌入任何 Python 应用的 AI 对话 SDK。
    
    特性:
        - 同步/异步/流式对话
        - RAG 知识库增强
        - 记忆管理
        - 自定义工具
        - Skills 技能
        - MCP 协议扩展
    
    使用示例::
    
        from agentic_sdk import ChatBot
        
        # 基础用法
        bot = ChatBot()
        response = bot.chat("你好")
        print(response.text)
        
        # 流式输出
        for chunk in bot.chat_stream("讲个故事"):
            print(chunk.content, end="", flush=True)
        
        # 添加自定义工具
        @bot.tool
        def calculate(expression: str) -> str:
            return str(eval(expression))
        
        response = bot.chat("计算 123 * 456")
    """
    
    def __init__(self, config: Optional[ChatConfig] = None):
        """
        初始化 ChatBot
        
        Args:
            config: 配置对象，默认使用标准配置
        """
        self.config = config or ChatConfig()
        self._initialized = False
        self._custom_tools: List[Callable] = []
        self._conversations: Dict[str, Conversation] = {}
        
        # 延迟初始化核心组件
        self._orchestrator = None
        self._llm_client = None
        self._rag_retriever = None
        self._memory_manager = None
        self._skills_manager = None
        
        # 配置日志
        self._setup_logging()
        
        logger.info(f"ChatBot SDK v{self._get_version()} initialized")
    
    def _setup_logging(self):
        """配置日志"""
        logger.remove()
        
        log_format = "<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}"
        
        # 控制台输出
        logger.add(
            sys.stderr,
            format=log_format,
            level=self.config.log_level,
        )
        
        # 文件输出
        if self.config.log_file:
            logger.add(
                self.config.log_file,
                format=log_format,
                level=self.config.log_level,
                rotation="10 MB",
            )
    
    def _get_version(self) -> str:
        """获取版本号"""
        try:
            from . import __version__
            return __version__
        except ImportError:
            return "0.1.0"
    
    def _ensure_initialized(self):
        """确保核心组件已初始化"""
        if self._initialized:
            return
        
        # 添加 backend 到路径
        backend_path = Path(__file__).parent.parent / "backend"
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))
        
        # 加载 .env 文件
        env_file = backend_path / ".env"
        if env_file.exists():
            from dotenv import load_dotenv
            load_dotenv(env_file)
            logger.info(f"Loaded environment from {env_file}")
        
        # 初始化核心组件
        from app.llm import get_llm_client
        from app.core.cursor_style_orchestrator import CursorStyleOrchestrator
        from app.core.practical_tools import get_practical_tools
        
        self._llm_client = get_llm_client()
        
        # 合并工具
        all_tools = get_practical_tools() + self._custom_tools
        
        self._orchestrator = CursorStyleOrchestrator(
            llm_client=self._llm_client,
            tools=all_tools,
            enable_rag=self.config.enable_rag,
            enable_skills=self.config.enable_skills,
            enable_memory=self.config.enable_memory,
            enable_preferences=self.config.enable_preferences,
        )
        
        self._initialized = True
        logger.info("ChatBot core components initialized")
    
    def _get_or_create_session(self, session_id: Optional[str] = None) -> str:
        """获取或创建会话"""
        if session_id and session_id in self._conversations:
            return session_id
        
        new_id = session_id or str(uuid.uuid4())[:8]
        self._conversations[new_id] = Conversation(session_id=new_id)
        return new_id
    
    # ==================== 核心对话 API ====================
    
    def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        **kwargs,
    ) -> ChatResponse:
        """
        同步对话
        
        Args:
            message: 用户消息
            session_id: 会话 ID（可选，自动生成）
            **kwargs: 额外参数
        
        Returns:
            ChatResponse: 对话响应
        
        Example::
        
            response = bot.chat("你好")
            print(response.text)
        """
        # 运行异步版本
        return asyncio.get_event_loop().run_until_complete(
            self.chat_async(message, session_id, **kwargs)
        )
    
    async def chat_async(
        self,
        message: str,
        session_id: Optional[str] = None,
        **kwargs,
    ) -> ChatResponse:
        """
        异步对话
        
        Args:
            message: 用户消息
            session_id: 会话 ID
            **kwargs: 额外参数
        
        Returns:
            ChatResponse: 对话响应
        
        Example::
        
            response = await bot.chat_async("你好")
            print(response.text)
        """
        self._ensure_initialized()
        
        session_id = self._get_or_create_session(session_id)
        start_time = datetime.now()
        
        # 收集流式响应
        text_parts = []
        tool_calls = []
        sources = []
        
        async for chunk in self._orchestrator.chat_stream(message, session_id):
            if chunk.type == "text":
                text_parts.append(chunk.content or "")
            elif chunk.type == "tool_call":
                tool_calls.append(ToolCall(
                    id=str(len(tool_calls)),
                    name=chunk.tool_name or "",
                    arguments=chunk.tool_args or {},
                ))
            elif chunk.type == "tool_result":
                if tool_calls:
                    tool_calls[-1].result = chunk.content
            elif chunk.type == "rag_result":
                sources.extend(chunk.metadata.get("sources", []))
        
        # 计算延迟
        latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # 更新对话历史
        conversation = self._conversations[session_id]
        conversation.add_message(MessageRole.USER, message)
        conversation.add_message(MessageRole.ASSISTANT, "".join(text_parts))
        
        return ChatResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            sources=sources,
            session_id=session_id,
            latency_ms=latency_ms,
        )
    
    def chat_stream(
        self,
        message: str,
        session_id: Optional[str] = None,
        **kwargs,
    ) -> Iterator[ChatChunk]:
        """
        流式对话（同步迭代器）
        
        Args:
            message: 用户消息
            session_id: 会话 ID
            **kwargs: 额外参数
        
        Yields:
            ChatChunk: 响应块
        
        Example::
        
            for chunk in bot.chat_stream("讲个故事"):
                if chunk.is_text:
                    print(chunk.content, end="", flush=True)
        """
        async def _stream():
            async for chunk in self.chat_stream_async(message, session_id, **kwargs):
                yield chunk
        
        # 同步包装异步生成器
        loop = asyncio.new_event_loop()
        try:
            agen = _stream()
            while True:
                try:
                    chunk = loop.run_until_complete(agen.__anext__())
                    yield chunk
                except StopAsyncIteration:
                    break
        finally:
            loop.close()
    
    async def chat_stream_async(
        self,
        message: str,
        session_id: Optional[str] = None,
        **kwargs,
    ):
        """
        流式对话（异步生成器）
        
        Args:
            message: 用户消息
            session_id: 会话 ID
            **kwargs: 额外参数
        
        Yields:
            ChatChunk: 响应块
        
        Example::
        
            async for chunk in bot.chat_stream_async("讲个故事"):
                if chunk.is_text:
                    print(chunk.content, end="", flush=True)
        """
        self._ensure_initialized()
        
        session_id = self._get_or_create_session(session_id)
        
        async for chunk in self._orchestrator.chat_stream(message, session_id):
            # StreamChunk 的额外信息在 metadata 中
            metadata = chunk.metadata or {}
            
            yield ChatChunk(
                type=chunk.type,
                content=chunk.content or "",
                tool_name=metadata.get("tool_name"),
                tool_args=metadata.get("tool_args"),
                tool_result=metadata.get("tool_result"),
                step=metadata.get("step"),
                total_steps=metadata.get("total_steps"),
                metadata=metadata,
            )
    
    # ==================== 工具管理 ====================
    
    def tool(self, func: Callable = None, *, name: str = None, description: str = None):
        """
        注册自定义工具的装饰器
        
        Args:
            func: 工具函数
            name: 工具名称（默认使用函数名）
            description: 工具描述（默认使用 docstring）
        
        Example::
        
            @bot.tool
            def get_weather(city: str) -> str:
                '''获取城市天气'''
                return f"{city}: 晴，25°C"
            
            @bot.tool(name="calc", description="数学计算")
            def calculate(expr: str) -> str:
                return str(eval(expr))
        """
        def decorator(f):
            # 使用 LangChain 的 tool 装饰器
            from langchain_core.tools import tool as lc_tool
            
            wrapped = lc_tool(f)
            if name:
                wrapped.name = name
            if description:
                wrapped.description = description
            
            self._custom_tools.append(wrapped)
            
            # 如果已初始化，需要重新注册工具
            if self._initialized and self._orchestrator:
                self._orchestrator.tool_orchestrator.register(wrapped)
            
            logger.info(f"Registered custom tool: {wrapped.name}")
            return f
        
        if func is not None:
            return decorator(func)
        return decorator
    
    def add_tool(self, tool: Callable):
        """
        添加工具（非装饰器方式）
        
        Args:
            tool: 工具函数或 StructuredTool
        
        Example::
        
            def my_tool(x: int) -> int:
                return x * 2
            
            bot.add_tool(my_tool)
        """
        from langchain_core.tools import tool as lc_tool, StructuredTool
        
        if not isinstance(tool, StructuredTool):
            tool = lc_tool(tool)
        
        self._custom_tools.append(tool)
        
        if self._initialized and self._orchestrator:
            self._orchestrator.tool_orchestrator.register(tool)
        
        logger.info(f"Added tool: {getattr(tool, 'name', tool.__name__)}")
    
    def list_tools(self) -> List[Dict[str, str]]:
        """
        列出所有可用工具
        
        Returns:
            工具信息列表
        """
        self._ensure_initialized()
        
        tools = []
        for name, meta in self._orchestrator.tool_orchestrator.metadata.items():
            tools.append({
                "name": name,
                "description": meta.description,
                "category": meta.category,
            })
        return tools
    
    # ==================== 知识库管理 ====================
    
    def load_documents(
        self,
        paths: Union[str, List[str]],
        **kwargs,
    ) -> int:
        """
        加载文档到知识库
        
        Args:
            paths: 文档路径（文件或目录）
            **kwargs: 额外参数
        
        Returns:
            加载的文档数量
        
        Example::
        
            count = bot.load_documents(["./docs/manual.pdf", "./docs/faq/"])
            print(f"Loaded {count} documents")
        """
        if not self.config.enable_rag:
            logger.warning("RAG is disabled, documents will not be loaded")
            return 0
        
        self._ensure_initialized()
        
        if isinstance(paths, str):
            paths = [paths]
        
        # 使用后端的文档处理器
        from app.rag.document_processor import DocumentProcessor
        from app.rag.vector_store import VectorStore
        
        processor = DocumentProcessor()
        vector_store = VectorStore()
        
        total = 0
        for path in paths:
            path = Path(path)
            
            if path.is_file():
                files = [path]
            elif path.is_dir():
                files = list(path.rglob("*"))
            else:
                logger.warning(f"Path not found: {path}")
                continue
            
            for file in files:
                if file.is_file() and file.suffix.lower() in [".pdf", ".txt", ".md", ".docx", ".html"]:
                    try:
                        chunks = processor.process_file(str(file))
                        if chunks:
                            vector_store.add_documents(chunks)
                            total += 1
                            logger.info(f"Loaded: {file.name}")
                    except Exception as e:
                        logger.error(f"Failed to load {file}: {e}")
        
        logger.info(f"Total documents loaded: {total}")
        return total
    
    def search_knowledge(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        搜索知识库
        
        Args:
            query: 搜索查询
            top_k: 返回结果数量
        
        Returns:
            搜索结果列表
        """
        if not self.config.enable_rag:
            return []
        
        self._ensure_initialized()
        
        from app.rag.retriever import RAGRetriever
        
        retriever = RAGRetriever()
        results = asyncio.get_event_loop().run_until_complete(
            retriever.retrieve(query, top_k=top_k)
        )
        return results
    
    # ==================== 会话管理 ====================
    
    def get_conversation(self, session_id: str) -> Optional[Conversation]:
        """获取对话历史"""
        return self._conversations.get(session_id)
    
    def clear_conversation(self, session_id: str):
        """清除对话历史"""
        if session_id in self._conversations:
            self._conversations[session_id].messages.clear()
            logger.info(f"Cleared conversation: {session_id}")
    
    def list_sessions(self) -> List[str]:
        """列出所有会话"""
        return list(self._conversations.keys())
    
    # ==================== Skills 管理 ====================
    
    def list_skills(self) -> List[Dict[str, Any]]:
        """列出所有技能"""
        if not self.config.enable_skills:
            return []
        
        self._ensure_initialized()
        
        skills = []
        for skill in self._orchestrator.skill_manager.list_skills():
            skills.append({
                "id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "category": skill.category,
                "triggers": skill.triggers,
            })
        return skills
    
    # ==================== 上下文管理器 ====================
    
    def __enter__(self):
        """支持 with 语句"""
        self._ensure_initialized()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """清理资源"""
        self.close()
    
    def close(self):
        """关闭并释放资源"""
        self._conversations.clear()
        self._initialized = False
        logger.info("ChatBot closed")


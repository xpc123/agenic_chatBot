"""
核心 Agent 引擎 - 主控制器
基于 LangChain 1.0 create_agent

这是应用的核心协调器，负责:
1. 接收用户输入
2. 处理 @路径引用（Context Loading）
3. RAG 知识检索
4. 调用 LangChain Agent 执行 ReAct 循环
5. 管理对话记忆
6. 生成并返回响应
"""
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable
from loguru import logger
from datetime import datetime

from ..models.chat import ChatMessage, MessageRole
from ..config import settings
from .memory import MemoryManager
from .executor import ToolExecutor
from .context_loader import ContextLoader
from .langchain_agent import LangChainAgent, AgentContext
from .tools import calculator, get_current_time, search_web, get_basic_tools
from ..llm import get_llm_client


class AgentEngine:
    """
    核心 Agent 引擎
    
    基于 LangChain 1.0 create_agent 实现，是应用的主要入口点。
    
    架构说明:
    - 使用 LangChainAgent 作为底层执行引擎
    - 通过 Middleware 实现上下文注入、错误处理、历史压缩等
    - 支持 RAG 检索增强
    - 支持 @路径引用加载本地文件
    
    使用示例:
    ```python
    engine = AgentEngine(memory_manager=memory)
    
    async for chunk in engine.chat("你好", session_id="123"):
        print(chunk)
    ```
    """
    
    def __init__(
        self,
        memory_manager: MemoryManager,
        tool_executor: Optional[ToolExecutor] = None,
        context_loader: Optional[ContextLoader] = None,
        tools: Optional[List[Callable]] = None,
        enable_summarization: bool = True,
        enable_pii_filter: bool = False,
        enable_human_in_loop: bool = False,
        human_approval_tools: Optional[List[str]] = None,
        enable_todo_list: bool = False,
    ):
        """
        初始化 Agent 引擎
        
        Args:
            memory_manager: 记忆管理器
            tool_executor: 工具执行器（可选，用于 MCP 工具）
            context_loader: 上下文加载器（可选）
            tools: 额外的工具列表
            enable_summarization: 是否启用对话历史压缩
            enable_pii_filter: 是否启用 PII 过滤
            enable_human_in_loop: 是否启用人工审批
            human_approval_tools: 需要人工审批的工具名称
            enable_todo_list: 是否启用任务列表
        """
        self.memory = memory_manager
        self.executor = tool_executor
        self.context_loader = context_loader or ContextLoader()
        
        # 构建工具列表：内置工具 + 自定义工具 + MCP 工具
        all_tools = self._build_tools(tools)
        
        # 初始化 LangChain Agent（使用 LangChain 1.0 create_agent）
        self.langchain_agent = LangChainAgent(
            tools=all_tools,
            model=settings.OPENAI_MODEL,
            enable_summarization=enable_summarization,
            enable_pii_filter=enable_pii_filter,
            enable_human_in_loop=enable_human_in_loop,
            human_approval_tools=human_approval_tools,
            enable_todo_list=enable_todo_list,
            max_iterations=settings.MAX_ITERATIONS,
        )
        
        self.enable_path_reference = settings.ENABLE_PATH_REFERENCE
        
        logger.info(
            f"AgentEngine initialized with LangChain 1.0 create_agent, "
            f"tools={len(all_tools)}, path_reference={self.enable_path_reference}"
        )
    
    def _build_tools(self, custom_tools: Optional[List[Callable]] = None) -> List[Callable]:
        """
        构建工具列表
        
        优先级:
        1. 内置工具 (calculator, get_current_time, etc.)
        2. 自定义工具 (用户传入)
        3. MCP 工具 (如果配置了)
        """
        # 内置工具
        builtin_tools = [calculator, get_current_time, search_web]
        
        # 自定义工具
        user_tools = custom_tools or []
        
        # MCP 工具 (从 executor 获取)
        mcp_tools = []
        if self.executor:
            try:
                mcp_tools = self.executor.get_langchain_tools()
            except Exception as e:
                logger.warning(f"Failed to load MCP tools: {e}")
        
        return builtin_tools + user_tools + mcp_tools
    
    async def chat(
        self,
        message: str,
        session_id: str,
        stream: bool = True,
        use_rag: bool = True,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        主对话方法 - 流式输出
        
        处理流程:
        1. 处理 @路径引用
        2. RAG 检索
        3. 保存用户消息
        4. 调用 Agent
        5. 保存 AI 回复
        
        Args:
            message: 用户消息
            session_id: 会话 ID
            stream: 是否流式输出（始终为 True，保持兼容性）
            use_rag: 是否使用 RAG 检索
            context: 额外上下文
        
        Yields:
            响应块 {"type": "text|tool_call|tool_result|context|sources|error", ...}
        """
        logger.info(f"Processing message for session {session_id}: {message[:50]}...")
        
        # 1. 处理 @路径引用
        path_context = None
        if self.enable_path_reference:
            path_context = await self._load_path_references(message)
            if path_context:
                yield {
                    "type": "context",
                    "content": f"📎 加载了 {path_context.get('references_count', 0)} 个引用",
                    "metadata": {
                        "contexts": path_context.get("contexts", []),
                    }
                }
        
        # 2. RAG 检索
        rag_results = None
        if use_rag:
            rag_data = await self._retrieve_knowledge(message, session_id)
            if rag_data:
                rag_results = rag_data["sources"]
                yield {
                    "type": "sources",
                    "content": rag_results,
                    "metadata": {"count": len(rag_results)}
                }
        
        # 3. 保存用户消息到记忆
        await self.memory.add_message(
            session_id,
            ChatMessage(role=MessageRole.USER, content=message)
        )
        
        # 4. 使用 LangChain Agent 执行
        final_response = ""
        agent_context = AgentContext(
            session_id=session_id,
            user_id=context.get("user_id", "") if context else "",
            rag_enabled=use_rag,
            extra_context=context,
        )
        
        async for chunk in self.langchain_agent.chat(
            message=message,
            session_id=session_id,
            rag_results=rag_results,
            path_context=path_context,
            context=agent_context,
        ):
            yield chunk
            # 累积最终回复
            if chunk.get("type") == "text":
                final_response = chunk.get("content", "")
        
        # 5. 保存 AI 回复到记忆
        if final_response:
            await self.memory.add_message(
                session_id,
                ChatMessage(role=MessageRole.ASSISTANT, content=final_response)
            )
            logger.info(f"Response saved for session {session_id}")
    
    async def _load_path_references(self, message: str) -> Optional[Dict[str, Any]]:
        """
        处理 @路径引用
        
        支持格式:
        - @/path/to/file.py (绝对路径)
        - @./relative/path.md (相对路径)
        - @path/to/directory/ (目录)
        """
        try:
            loaded_context = await self.context_loader.load_context_from_message(message)
            if loaded_context.get("contexts"):
                formatted_context = await self.context_loader.format_context_for_llm(
                    loaded_context["contexts"]
                )
                loaded_context["formatted"] = formatted_context
                return loaded_context
        except Exception as e:
            logger.error(f"Failed to load path references: {e}")
        
        return None
    
    async def _retrieve_knowledge(
        self, 
        query: str, 
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        从 RAG 系统检索相关知识
        
        Args:
            query: 查询文本
            session_id: 会话 ID
        
        Returns:
            检索结果字典，包含 sources 和 context
        """
        try:
            from ..rag.retriever import retriever
            
            results = await retriever.retrieve(
                query=query,
                top_k=settings.TOP_K_RETRIEVAL,
            )
            
            if not results:
                return None
            
            return {
                "sources": results,
                "context": "\n\n".join([r.get("content", "") for r in results]),
            }
        except ImportError:
            logger.debug("RAG retriever not available")
            return None
        except Exception as e:
            logger.error(f"RAG retrieval error: {e}")
            return None
    
    def add_tool(self, tool_func: Callable):
        """
        动态添加工具到 Agent
        
        Args:
            tool_func: 使用 @tool 装饰器的函数
        """
        self.langchain_agent.add_tool(tool_func)
        logger.info(f"Tool added to AgentEngine: {tool_func.__name__}")
    
    async def invoke(
        self,
        message: str,
        session_id: str,
        use_rag: bool = True,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        同步调用接口（非流式）
        
        Args:
            message: 用户消息
            session_id: 会话 ID
            use_rag: 是否使用 RAG
            context: 额外上下文
        
        Returns:
            最终回复文本
        """
        # 处理 @路径引用
        path_context = None
        if self.enable_path_reference:
            path_context = await self._load_path_references(message)
        
        # RAG 检索
        rag_results = None
        if use_rag:
            rag_data = await self._retrieve_knowledge(message, session_id)
            if rag_data:
                rag_results = rag_data["sources"]
        
        # 保存用户消息
        await self.memory.add_message(
            session_id,
            ChatMessage(role=MessageRole.USER, content=message)
        )
        
        # 调用 Agent
        agent_context = AgentContext(
            session_id=session_id,
            user_id=context.get("user_id", "") if context else "",
            rag_enabled=use_rag,
            extra_context=context,
        )
        
        response = self.langchain_agent.invoke(
            message=message,
            session_id=session_id,
            rag_results=rag_results,
            path_context=path_context,
            context=agent_context,
        )
        
        # 保存回复
        if response:
            await self.memory.add_message(
                session_id,
                ChatMessage(role=MessageRole.ASSISTANT, content=response)
            )
        
        return response
    
    async def clear_history(self, session_id: str) -> bool:
        """
        清除会话历史
        
        Args:
            session_id: 会话 ID
        
        Returns:
            是否成功
        """
        try:
            await self.memory.clear_session(session_id)
            logger.info(f"Session history cleared: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear session history: {e}")
            return False
    
    async def get_history(
        self, 
        session_id: str, 
        max_messages: Optional[int] = None
    ) -> List[ChatMessage]:
        """
        获取会话历史
        
        Args:
            session_id: 会话 ID
            max_messages: 最大消息数
        
        Returns:
            消息列表
        """
        return await self.memory.get_conversation_history(
            session_id, 
            max_messages=max_messages
        )

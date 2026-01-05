# -*- coding: utf-8 -*-
"""
对话协调器 - 业务编排层

这是应用的核心协调器（Orchestrator），负责:
1. 接收用户输入
2. 处理 @路径引用（Context Loading）
3. RAG 知识检索
4. 统一上下文管理（Context Engineering）
5. 调用 ExecutorAgent 执行 ReAct 循环
6. 管理对话记忆
7. 生成并返回响应

架构说明:
- Orchestrator 是高层业务协调器（不是 Agent）
- ExecutorAgent 是底层 Agent 执行引擎（真正的 Agent）
- ContextManager 统一管理所有上下文来源
"""
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable
from loguru import logger
from datetime import datetime

from ..models.chat import ChatMessage, MessageRole
from ..config import settings
from .memory import MemoryManager
from .tool_executor import ToolExecutor
from .context_loader import ContextLoader
from .context_manager import ContextManager
from .agent_engine import ExecutorAgent, AgentContext
from .tools import get_current_time, get_basic_tools, run_python_code
from ..llm import get_llm_client


class Orchestrator:
    """
    对话协调器 - 业务编排层
    
    负责协调各个模块工作，是应用的主要入口点。
    注意：这不是 Agent，而是协调器/编排器。
    
    架构说明:
    - 使用 ExecutorAgent 作为底层执行引擎（真正的 Agent）
    - 使用 ContextManager 统一管理上下文（Context Engineering）
    - 通过 Middleware 实现上下文注入、错误处理、历史压缩等
    - 支持 RAG 检索增强
    - 支持 @路径引用加载本地文件
    
    使用示例:
    ```python
    orchestrator = Orchestrator(memory_manager=memory)
    
    async for chunk in orchestrator.chat("你好", session_id="123"):
        print(chunk)
    ```
    """
    
    def __init__(
        self,
        memory_manager: MemoryManager,
        tool_executor: Optional[ToolExecutor] = None,
        context_loader: Optional[ContextLoader] = None,
        tools: Optional[List[Callable]] = None,
        enable_summarization: bool = False,  # 默认禁用，需要 OpenAI key
        enable_pii_filter: bool = False,
        enable_human_in_loop: bool = False,
        human_approval_tools: Optional[List[str]] = None,
        enable_todo_list: bool = False,
    ):
        """
        初始化协调器
        
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
        
        # 初始化 Agent 执行器
        # 确定使用的模型和提供商
        provider = settings.LLM_PROVIDER
        model_name = settings.JEDAI_MODEL if provider == "jedai" else settings.OPENAI_MODEL
        
        self.agent_executor = ExecutorAgent(
            tools=all_tools,
            model=model_name,
            provider=provider,
            enable_summarization=enable_summarization,
            enable_pii_filter=enable_pii_filter,
            enable_human_in_loop=enable_human_in_loop,
            human_approval_tools=human_approval_tools,
            enable_todo_list=enable_todo_list,
            max_iterations=settings.MAX_ITERATIONS,
        )
        
        self.enable_path_reference = settings.ENABLE_PATH_REFERENCE
        
        # Context Engineering: 上下文 Token 预算配置
        self.context_max_tokens = getattr(settings, 'CONTEXT_MAX_TOKENS', 8000)
        self.context_reserve_tokens = getattr(settings, 'CONTEXT_RESERVE_TOKENS', 2000)
        
        logger.info(
            f"Orchestrator initialized, "
            f"tools={len(all_tools)}, path_reference={self.enable_path_reference}, "
            f"context_budget={self.context_max_tokens}"
        )
    
    def _build_tools(self, custom_tools: Optional[List[Callable]] = None) -> List[Callable]:
        """
        构建工具列表
        
        优先级:
        1. 内置工具 (get_current_time, run_python_code, etc.)
        2. 自定义工具 (用户传入)
        3. MCP 工具 (如果配置了)
        """
        # 内置工具
        builtin_tools = [get_current_time, run_python_code]
        
        # 自定义工具
        user_tools = custom_tools or []
        
        # MCP 工具 (从 executor 获取)
        mcp_tools = []
        if self.executor:
            try:
                mcp_tools = self.executor.get_langchain_tools()
            except Exception as e:
                logger.warning(f"Failed to get MCP tools: {e}")
        
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
        1. 创建 ContextManager（统一上下文管理）
        2. 处理 @路径引用
        3. RAG 检索
        4. 获取对话历史
        5. 获取用户偏好（长期记忆）
        6. 构建统一上下文
        7. 保存用户消息
        8. 调用 Agent
        9. 保存 AI 回复
        
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
        
        # ========== Context Engineering: 统一上下文管理 ==========
        ctx_manager = ContextManager(
            max_tokens=self.context_max_tokens,
            reserve_tokens=self.context_reserve_tokens,
        )
        
        # 1. 处理 @路径引用（高优先级）
        path_context = None
        if self.enable_path_reference:
            path_context = await self._load_path_references(message)
            if path_context:
                ctx_manager.add_path_references(path_context)
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
                ctx_manager.add_rag_results(rag_results)
                yield {
                    "type": "sources",
                    "content": rag_results,
                    "metadata": {"count": len(rag_results)}
                }
        
        # 3. 获取对话历史
        conversation_history = await self.memory.get_history(session_id)
        if conversation_history:
            history_messages = [
                {"role": msg.role.value, "content": msg.content}
                for msg in conversation_history
            ]
            ctx_manager.add_conversation_history(history_messages)
        
        # 4. 获取用户偏好（长期记忆，如果支持）
        if hasattr(self.memory, 'get_user_preferences'):
            user_id = context.get("user_id", "") if context else ""
            if user_id:
                preferences = await self.memory.get_user_preferences(user_id)
                if preferences:
                    ctx_manager.add_user_preferences(preferences)
        
        # 5. 构建统一上下文
        unified_context = ctx_manager.build()
        context_stats = ctx_manager.get_stats()
        logger.info(f"Context built: {context_stats['total_items']} items, "
                   f"{context_stats['utilization_percent']} utilization")
        
        # 6. 保存用户消息到记忆
        await self.memory.add_message(
            session_id,
            ChatMessage(role=MessageRole.USER, content=message)
        )
        
        # 7. 使用 Agent 执行
        final_response = ""
        agent_context = AgentContext(
            session_id=session_id,
            user_id=context.get("user_id", "") if context else "",
            rag_enabled=use_rag,
            extra_context=context,
        )
        
        async for chunk in self.agent_executor.chat(
            message=message,
            session_id=session_id,
            unified_context=unified_context,  # 使用统一上下文
            context=agent_context,
        ):
            yield chunk
            # 累积最终回复
            if chunk.get("type") == "text":
                final_response = chunk.get("content", "")
        
        # 8. 保存 AI 回复到记忆
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
        self.agent_executor.add_tool(tool_func)
        logger.info(f"Tool added to Orchestrator: {tool_func.__name__}")
    
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
        
        response = self.agent_executor.invoke(
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


# 向后兼容别名
AgentOrchestrator = Orchestrator

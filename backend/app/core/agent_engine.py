# -*- coding: utf-8 -*-
"""
基于 LangChain 1.0 的 Agent 实现
使用 create_agent + Middleware 模式

LangChain 1.0 核心特性:
- create_agent: 标准 Agent 创建 API
- Middleware: 可组合的中间件架构（before_model, after_model, wrap_tool_call 等）
- 内置中间件: SummarizationMiddleware, PIIMiddleware, HumanInTheLoopMiddleware 等
- 基于 LangGraph: 自动支持持久化、流式输出、人工审批
"""
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable
from dataclasses import dataclass
from loguru import logger

# LangChain 1.0 核心导入
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import (
    AgentMiddleware,
    SummarizationMiddleware,
    HumanInTheLoopMiddleware,
    ModelCallLimitMiddleware,
    ToolRetryMiddleware,
    ModelRetryMiddleware,
    PIIMiddleware,
    ModelFallbackMiddleware,
    ToolCallLimitMiddleware,
    TodoListMiddleware,
    before_model,
    after_model,
    wrap_tool_call,
    wrap_model_call,
    dynamic_prompt,
    ModelRequest,
    ModelResponse,
)
from langchain.tools import tool, ToolRuntime
from langchain.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

from ..models.chat import ChatMessage, MessageRole
from ..config import settings


# ==================== 自定义上下文类型 ====================

@dataclass
class AgentContext:
    """
    Agent 运行时上下文
    
    用于在 middleware 和 tools 之间传递自定义数据
    """
    session_id: str = ""
    user_id: str = ""
    rag_enabled: bool = True
    extra_context: Optional[Dict[str, Any]] = None


# ==================== 自定义中间件 ====================

class RAGContextMiddleware(AgentMiddleware):
    """
    上下文注入中间件
    
    支持两种模式：
    1. 统一上下文模式（推荐）：使用 ContextManager 预构建的统一上下文
    2. 分散上下文模式（兼容）：分别传入 RAG 结果和 @路径引用
    
    在调用模型前，将上下文注入到提示中
    """
    
    def __init__(self):
        self.unified_context: Optional[str] = None  # 统一上下文（推荐）
        self.rag_results: Optional[List[Dict[str, Any]]] = None
        self.path_context: Optional[Dict[str, Any]] = None
    
    def set_unified_context(self, unified_context: str):
        """
        设置统一上下文（推荐方式）
        
        Args:
            unified_context: 由 ContextManager.build() 生成的统一上下文
        """
        self.unified_context = unified_context
        # 清除分散上下文
        self.rag_results = None
        self.path_context = None
    
    def set_context(
        self, 
        rag_results: Optional[List[Dict[str, Any]]] = None,
        path_context: Optional[Dict[str, Any]] = None
    ):
        """设置分散上下文（兼容旧接口）"""
        self.rag_results = rag_results
        self.path_context = path_context
        # 清除统一上下文
        self.unified_context = None
    
    def before_model(self, state: AgentState, runtime) -> Dict[str, Any] | None:
        """在调用模型前注入上下文"""
        context_content = None
        
        # 优先使用统一上下文
        if self.unified_context:
            context_content = self.unified_context
        else:
            # 兼容模式：构建分散上下文
            context_parts = []
            
            # 注入 RAG 检索结果
            if self.rag_results:
                context_parts.append("## 📚 知识库参考")
                for i, doc in enumerate(self.rag_results[:5], 1):  # 最多5条
                    content = doc.get('content', '')[:500]
                    source = doc.get('source', 'unknown')
                    score = doc.get('score', 0)
                    context_parts.append(f"### 引用 {i} (相关度: {score:.2f})")
                    context_parts.append(f"**来源**: {source}")
                    context_parts.append(f"**内容**: {content}...")
                context_parts.append("")
            
            # 注入 @路径引用内容
            if self.path_context and self.path_context.get("formatted"):
                context_parts.append("## 📎 引用的文件内容")
                context_parts.append(self.path_context["formatted"])
                context_parts.append("")
            
            if context_parts:
                context_content = "\n".join(context_parts)
        
        if context_content:
            # 将上下文作为系统消息注入到消息列表开头
            context_message = SystemMessage(content=context_content)
            messages = list(state.get("messages", []))
            # 在第一条用户消息之前插入上下文
            messages.insert(0, context_message)
            return {"messages": messages}
        
        return None
    
    def clear_context(self):
        """清除所有上下文"""
        self.unified_context = None
        self.rag_results = None
        self.path_context = None


@before_model
def log_model_request(request: ModelRequest) -> None:
    """记录模型调用日志"""
    message_count = len(request.state.get("messages", []))
    logger.debug(f"Model request: {message_count} messages")


@after_model
def log_model_response(state: AgentState, response, runtime) -> None:
    """记录模型响应日志"""
    if hasattr(response, 'content') and response.content:
        content_preview = response.content[:100] + "..." if len(response.content) > 100 else response.content
        logger.debug(f"Model response: {content_preview}")


@wrap_tool_call
async def enhanced_tool_error_handler(request, handler):
    """
    增强的工具错误处理中间件（异步版本）
    
    提供更友好的错误消息和自动重试建议
    """
    try:
        return await handler(request)
    except Exception as e:
        tool_name = request.tool_call.get("name", "unknown")
        error_msg = str(e)
        
        logger.error(f"Tool '{tool_name}' failed: {error_msg}")
        
        # 返回友好的错误消息
        return ToolMessage(
            content=(
                f"⚠️ 工具 '{tool_name}' 执行失败\n"
                f"错误: {error_msg}\n"
                f"建议: 请检查输入参数是否正确，或稍后重试。"
            ),
            tool_call_id=request.tool_call["id"]
        )


# ==================== 主 Agent 类 ====================

class ExecutorAgent:
    """
    执行 Agent - 底层执行引擎
    
    这是真正的 Agent，基于 LangChain 1.0 create_agent 实现，负责:
    - 执行 ReAct 循环（Reason → Act → Observe）
    - 管理 Middleware（压缩、PII、人工审批等）
    - 处理工具调用
    - 注入上下文到 LLM
    - 流式输出结果
    
    核心特性:
    - 使用 create_agent 构建标准 ReAct 循环
    - 支持丰富的内置 Middleware
    - 自动持久化和流式输出
    - 动态工具和模型选择
    - 自定义上下文注入
    
    使用示例:
    ```python
    agent = ExecutorAgent(
        tools=[my_tool],
        model="gpt-4o",
        enable_summarization=True,
    )
    
    async for chunk in agent.chat(message, session_id):
        print(chunk)
    ```
    """
    
    def __init__(
        self,
        tools: Optional[List[Callable]] = None,
        model: Optional[str] = None,
        provider: str = "openai", # 新增 provider 参数
        use_tool_registry: bool = True,  # 新增：使用工具注册表
        tool_categories: Optional[List[str]] = None,  # 新增：工具分类过滤
        enable_summarization: bool = False,  # 默认禁用，需要 OpenAI key
        enable_pii_filter: bool = False,
        enable_human_in_loop: bool = False,
        human_approval_tools: Optional[List[str]] = None,
        enable_todo_list: bool = False,
        enable_model_fallback: bool = False,  # 默认禁用，需要 OpenAI/Anthropic key
        fallback_models: Optional[List[str]] = None,
        max_iterations: Optional[int] = None,
    ):
        """
        初始化 LangChain Agent
        
        Args:
            tools: 工具列表（使用 @tool 装饰器定义），如果为 None 且 use_tool_registry=True，则从注册表获取
            model: 模型标识符 (如 "gpt-4o", "claude-sonnet-4-5-20250929")
            provider: 模型提供商 ("openai", "anthropic", "jedai", etc.)
            use_tool_registry: 是否使用工具注册表（默认 True）
            tool_categories: 从注册表获取工具时的分类过滤（如 ["builtin", "extended"]）
            enable_summarization: 是否启用对话历史自动压缩
            enable_pii_filter: 是否启用 PII 过滤
            enable_human_in_loop: 是否启用人工审批
            human_approval_tools: 需要人工审批的工具名称列表
            enable_todo_list: 是否启用任务列表功能
            enable_model_fallback: 是否启用模型故障切换
            fallback_models: 备用模型列表
            max_iterations: 最大迭代次数
        """
        # 处理工具列表
        if tools is not None:
            # 如果显式传入工具，使用传入的
            self.tools = tools
        elif use_tool_registry:
            # 从工具注册表获取
            registry = get_tool_registry()
            if registry.get_tool_names():
                # 注册表已初始化
                if tool_categories:
                    self.tools = registry.get_tools(categories=set(tool_categories))
                else:
                    self.tools = registry.get_all_tools()
                logger.info(f"📦 从注册表加载了 {len(self.tools)} 个工具")
            else:
                # 注册表为空，使用默认工具
                self.tools = get_basic_tools()
                logger.info(f"📦 使用默认工具: {len(self.tools)} 个")
        else:
            # 不使用注册表，使用默认工具
            self.tools = get_basic_tools()
        
        self.model_name = model or settings.OPENAI_MODEL
        self.provider = provider # 保存 provider
        self.max_iterations = max_iterations or settings.MAX_ITERATIONS
        
        # 持久化 checkpointer
        self.checkpointer = InMemorySaver()
        
        # 初始化 RAG 上下文中间件
        self.rag_context_middleware = RAGContextMiddleware()
        
        # 构建中间件列表
        self.middleware = self._build_middleware(
            enable_summarization=enable_summarization,
            enable_pii_filter=enable_pii_filter,
            enable_human_in_loop=enable_human_in_loop,
            human_approval_tools=human_approval_tools,
            enable_todo_list=enable_todo_list,
            enable_model_fallback=enable_model_fallback,
            fallback_models=fallback_models,
        )
        
        # 构建 Agent
        self.agent = self._build_agent()
        
        logger.info(
            f"ExecutorAgent initialized: model={self.model_name}, "
            f"tools={len(self.tools)}, middleware={len(self.middleware)}"
        )
    
    def _build_middleware(
        self,
        enable_summarization: bool,
        enable_pii_filter: bool,
        enable_human_in_loop: bool,
        human_approval_tools: Optional[List[str]],
        enable_todo_list: bool,
        enable_model_fallback: bool,
        fallback_models: Optional[List[str]],
    ) -> List:
        """构建中间件列表"""
        middleware = []
        
        # 1. RAG 上下文注入（自定义）
        middleware.append(self.rag_context_middleware)
        
        # 2. 日志中间件 (暂时禁用，可能有兼容性问题)
        # middleware.extend([log_model_request, log_model_response])
        
        # 3. 模型调用限制（防止无限循环）
        middleware.append(
            ModelCallLimitMiddleware(
                thread_limit=self.max_iterations * 2,
                run_limit=self.max_iterations,
                exit_behavior="end",
            )
        )
        
        # 4. 工具调用限制
        middleware.append(
            ToolCallLimitMiddleware(
                thread_limit=50,
                run_limit=20,
            )
        )
        
        # 5. 工具重试（处理临时失败）
        middleware.append(
            ToolRetryMiddleware(
                max_retries=3,
                backoff_factor=2.0,
                initial_delay=1.0,
            )
        )
        
        # 6. 模型重试（处理 API 临时失败）
        middleware.append(
            ModelRetryMiddleware(
                max_retries=3,
                backoff_factor=2.0,
                initial_delay=1.0,
            )
        )
        
        # 7. 增强的工具错误处理（异步版本）
        middleware.append(enhanced_tool_error_handler)
        
        # 8. 模型故障切换（可选）
        if enable_model_fallback:
            fallbacks = fallback_models or ["gpt-4o-mini", "claude-3-5-sonnet-20241022"]
            middleware.append(ModelFallbackMiddleware(*fallbacks))
        
        # 9. 历史压缩（可选）
        if enable_summarization:
            middleware.append(
                SummarizationMiddleware(
                    model="gpt-4o-mini",  # 使用较小模型进行摘要
                    trigger=("tokens", 4000),
                    keep=("messages", 20),
                )
            )
        
        # 10. PII 过滤（可选）
        if enable_pii_filter:
            middleware.extend([
                PIIMiddleware("email", strategy="redact", apply_to_input=True),
                PIIMiddleware("phone_number", strategy="mask", apply_to_input=True),
                PIIMiddleware("credit_card", strategy="block", apply_to_input=True),
            ])
        
        # 11. 任务列表（可选）
        if enable_todo_list:
            middleware.append(TodoListMiddleware())
        
        # 12. 人工审批（可选）
        if enable_human_in_loop and human_approval_tools:
            interrupt_config = {
                tool_name: {"allowed_decisions": ["approve", "edit", "reject"]}
                for tool_name in human_approval_tools
            }
            middleware.append(
                HumanInTheLoopMiddleware(interrupt_on=interrupt_config)
            )
        
        return middleware
    
    def _build_agent(self):
        """构建 LangChain 1.0 Agent"""
        system_prompt = self._get_system_prompt()
        
        # 获取 LLM 客户端实例
        # 注意：这里我们使用 get_llm_client 来获取统一管理的 LLM 实例
        # 这样可以复用 client.py 中的初始化逻辑（包括 JedAI 的特殊处理）
        from ..llm import get_llm_client
        llm_client = get_llm_client(provider=self.provider, model=self.model_name)
        
        # 使用 llm_client.llm 作为模型实例
        # create_agent 支持传入已初始化的 BaseChatModel
        agent = create_agent(
            model=llm_client.llm, 
            tools=self.tools,
            system_prompt=system_prompt,
            middleware=self.middleware,
            checkpointer=self.checkpointer,
            context_schema=AgentContext,
        )
        
        return agent
    
    def _get_system_prompt(self) -> str:
        """获取系统提示"""
        return """你是一个强大的 AI 助手，具有以下能力：

## 核心能力

1. **工具调用**: 你可以使用提供的工具来获取信息、执行操作
2. **上下文理解**: 你会收到来自知识库和文件引用的上下文信息
3. **多步推理**: 对于复杂问题，你会分步骤思考和执行
4. **任务规划**: 对于复杂任务，先制定计划再逐步执行

## 工作原则

- 仔细阅读用户问题，理解真正的意图
- 如果需要使用工具，先思考需要什么信息，再调用相应工具
- 使用提供的上下文信息（知识库、文件内容）来增强回答
- 回答要准确、有帮助、格式清晰
- 如果不确定，坦诚说明并提供可能的方向
- 优先使用中文回复

## 引用规范

当使用知识库或文件内容时，请在回答中标注来源。
格式: [来源: 文件名或链接]

## 工具使用建议

- 数学计算: 使用 calculator 工具
- 获取当前时间: 使用 get_current_time 工具
- 其他工具: 根据工具描述选择合适的工具"""
    
    def add_tool(self, tool_func: Callable):
        """
        动态添加工具
        
        Args:
            tool_func: 使用 @tool 装饰器定义的函数
        """
        self.tools.append(tool_func)
        # 重新构建 Agent
        self.agent = self._build_agent()
        logger.info(f"Tool added: {tool_func.__name__}")
    
    def set_context(
        self,
        unified_context: Optional[str] = None,
        rag_results: Optional[List[Dict[str, Any]]] = None,
        path_context: Optional[Dict[str, Any]] = None,
    ):
        """
        设置对话上下文
        
        Args:
            unified_context: 统一构建的上下文字符串（推荐使用 ContextManager）
            rag_results: RAG 检索结果（兼容旧接口）
            path_context: @路径引用上下文（兼容旧接口）
        """
        if unified_context:
            # 使用统一上下文（Context Engineering）
            self.rag_context_middleware.set_unified_context(unified_context)
        else:
            # 兼容旧接口
            self.rag_context_middleware.set_context(rag_results, path_context)
    
    async def chat(
        self,
        message: str,
        session_id: str,
        unified_context: Optional[str] = None,
        rag_results: Optional[List[Dict[str, Any]]] = None,
        path_context: Optional[Dict[str, Any]] = None,
        context: Optional[AgentContext] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式对话接口
        
        Args:
            message: 用户消息
            session_id: 会话 ID（用于持久化）
            unified_context: 统一构建的上下文（推荐，由 ContextManager 生成）
            rag_results: RAG 检索结果（兼容旧接口）
            path_context: @路径引用上下文（兼容旧接口）
            context: 自定义运行时上下文
        
        Yields:
            事件字典 {"type": "text|tool_call|tool_result|thinking|error", "content": ...}
        """
        # 设置上下文（优先使用统一上下文）
        self.set_context(unified_context, rag_results, path_context)
        
        # 准备输入
        input_data = {
            "messages": [{"role": "user", "content": message}]
        }
        
        # 配置（使用 session_id 实现会话持久化）
        config = {"configurable": {"thread_id": session_id}}
        
        # 运行时上下文
        runtime_context = context or AgentContext(session_id=session_id)
        
        # 跟踪已处理的工具调用和结果，避免重复
        seen_tool_calls = set()
        seen_tool_results = set()
        last_text_content = None
        
        try:
            # 流式执行
            async for chunk in self.agent.astream(
                input_data, 
                config, 
                stream_mode="values",
                context=runtime_context,
            ):
                # 解析最新消息
                messages = chunk.get("messages", [])
                if not messages:
                    continue
                
                last_message = messages[-1]
                
                # 处理工具调用（去重）
                if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                    for tool_call in last_message.tool_calls:
                        tool_call_id = tool_call.get("id", "")
                        if tool_call_id and tool_call_id in seen_tool_calls:
                            continue  # 跳过已处理的工具调用
                        seen_tool_calls.add(tool_call_id)
                        
                        yield {
                            "type": "tool_call",
                            "content": f"🔧 调用工具: {tool_call['name']}",
                            "metadata": {
                                "tool": tool_call["name"],
                                "args": tool_call.get("args", {}),
                                "tool_call_id": tool_call_id
                            }
                        }
                
                # 处理工具结果（去重）
                elif isinstance(last_message, ToolMessage):
                    tool_call_id = last_message.tool_call_id
                    if tool_call_id in seen_tool_results:
                        continue  # 跳过已处理的工具结果
                    seen_tool_results.add(tool_call_id)
                    
                    yield {
                        "type": "tool_result",
                        "content": f"✅ 工具结果",
                        "metadata": {
                            "tool_call_id": tool_call_id,
                            "result": last_message.content[:500]
                        }
                    }
                
                # 处理 AI 最终回复（去重）
                elif hasattr(last_message, "content") and last_message.content:
                    # 只有当没有工具调用时才是最终回复
                    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
                        # 避免重复发送相同内容
                        if last_message.content != last_text_content:
                            last_text_content = last_message.content
                            yield {
                                "type": "text",
                                "content": last_message.content
                            }
        
        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            yield {
                "type": "error",
                "content": f"❌ 执行出错: {str(e)}"
            }
        
        finally:
            # 清理上下文
            self.rag_context_middleware.clear_context()
    
    def invoke(
        self,
        message: str,
        session_id: str,
        rag_results: Optional[List[Dict[str, Any]]] = None,
        path_context: Optional[Dict[str, Any]] = None,
        context: Optional[AgentContext] = None,
    ) -> str:
        """
        同步调用接口（非流式）
        
        Returns:
            最终回复文本
        """
        self.set_context(rag_results, path_context)
        
        input_data = {
            "messages": [{"role": "user", "content": message}]
        }
        config = {"configurable": {"thread_id": session_id}}
        runtime_context = context or AgentContext(session_id=session_id)
        
        try:
            result = self.agent.invoke(input_data, config, context=runtime_context)
            
            # 提取最终回复
            messages = result.get("messages", [])
            for msg in reversed(messages):
                if hasattr(msg, "content") and msg.content:
                    if not hasattr(msg, "tool_calls") or not msg.tool_calls:
                        return msg.content
            
            return ""
        
        finally:
            self.rag_context_middleware.clear_context()


# ==================== 内置工具导入 ====================

from .tools import (
    calculator,
    get_current_time,
    get_current_date,
    search_web,
    get_builtin_tools,
    get_basic_tools,
    get_extended_tools,
)

from .tool_registry import (
    ToolRegistry,
    ToolPermission,
    get_tool_registry,
)


# ==================== 全局工具注册表 ====================

def init_tool_registry(
    load_builtin: bool = True,
    load_extended: bool = True,
    api_config_path: Optional[str] = None,
) -> ToolRegistry:
    """
    初始化全局工具注册表
    
    Args:
        load_builtin: 是否加载内置工具
        load_extended: 是否加载扩展工具（HTTP、系统信息等）
        api_config_path: API 工具配置文件路径
    
    Returns:
        初始化后的工具注册表
    """
    registry = get_tool_registry()
    
    # 加载内置工具
    if load_builtin:
        builtin_tools = get_builtin_tools()
        count = registry.register_many(
            builtin_tools, 
            permission=ToolPermission.PUBLIC, 
            category="builtin"
        )
        logger.info(f"📦 加载了 {count} 个内置工具")
    
    # 加载扩展工具
    if load_extended:
        extended_tools = get_extended_tools()
        count = registry.register_many(
            extended_tools,
            permission=ToolPermission.PUBLIC,
            category="extended"
        )
        logger.info(f"🔧 加载了 {count} 个扩展工具")
    
    # 加载 API 工具配置
    if api_config_path:
        import os
        if os.path.exists(api_config_path):
            count = registry.load_from_config(api_config_path)
            logger.info(f"🌐 从配置加载了 {count} 个 API 工具")
        else:
            logger.warning(f"API 配置文件不存在: {api_config_path}")
    
    return registry


def get_tools_from_registry(
    categories: Optional[List[str]] = None,
    exclude_tools: Optional[List[str]] = None,
) -> List:
    """
    从注册表获取工具列表
    
    Args:
        categories: 要包含的分类列表（None 表示全部）
        exclude_tools: 要排除的工具名称列表
    
    Returns:
        工具列表
    """
    registry = get_tool_registry()
    
    # 获取所有启用的工具
    if categories:
        tools = registry.get_tools(categories=set(categories))
    else:
        tools = registry.get_all_tools()
    
    # 排除指定工具
    if exclude_tools:
        tools = [t for t in tools if t.name not in exclude_tools]
    
    return tools


# 向后兼容别名
AgentExecutor = ExecutorAgent

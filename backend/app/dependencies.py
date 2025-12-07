"""
依赖注入 - 统一管理组件生命周期

LangChain 1.0 架构:
- AgentEngine 是核心入口，内部使用 LangChainAgent
- 单例模式管理共享资源（MemoryManager, ToolExecutor, ContextLoader）
- 每次请求创建新的 AgentEngine 实例（复用单例依赖）
"""
from typing import Optional
from functools import lru_cache

from .core.memory import MemoryManager
from .core.executor import ToolExecutor
from .core.context_loader import ContextLoader
from .core.agent import AgentEngine
from .mcp import mcp_registry
from .llm.client import get_llm_client
from .config import settings
from loguru import logger


# ==================== 单例组件 ====================

@lru_cache()
def get_memory_manager() -> MemoryManager:
    """获取内存管理器实例（单例）"""
    logger.debug("Creating MemoryManager instance")
    return MemoryManager()


@lru_cache()
def get_tool_executor() -> ToolExecutor:
    """获取工具执行器实例（单例）"""
    logger.debug("Creating ToolExecutor instance")
    return ToolExecutor(mcp_registry)


@lru_cache()
def get_context_loader() -> ContextLoader:
    """获取上下文加载器实例（单例）"""
    logger.debug("Creating ContextLoader instance")
    return ContextLoader()


# ==================== 每次请求创建 ====================

def get_agent_engine(
    memory_manager: Optional[MemoryManager] = None,
    tool_executor: Optional[ToolExecutor] = None,
    context_loader: Optional[ContextLoader] = None,
    enable_summarization: bool = True,
    enable_pii_filter: bool = False,
    enable_human_in_loop: bool = False,
    enable_todo_list: bool = False,
) -> AgentEngine:
    """
    获取 Agent 引擎实例
    
    基于 LangChain 1.0 create_agent 构建
    
    注意：每次请求都会创建新的 AgentEngine 实例，
    但会复用单例的依赖组件
    
    Args:
        memory_manager: 内存管理器（可选，默认使用单例）
        tool_executor: 工具执行器（可选，默认使用单例）
        context_loader: 上下文加载器（可选，默认使用单例）
        enable_summarization: 是否启用对话历史压缩
        enable_pii_filter: 是否启用 PII 过滤
        enable_human_in_loop: 是否启用人工审批
        enable_todo_list: 是否启用任务列表
    
    Returns:
        AgentEngine 实例
    """
    logger.debug("Creating AgentEngine instance")
    
    return AgentEngine(
        memory_manager=memory_manager or get_memory_manager(),
        tool_executor=tool_executor or get_tool_executor(),
        context_loader=context_loader or get_context_loader(),
        enable_summarization=enable_summarization,
        enable_pii_filter=enable_pii_filter,
        enable_human_in_loop=enable_human_in_loop,
        enable_todo_list=enable_todo_list,
    )


# ==================== 清理函数 ====================

def clear_singleton_cache():
    """清理单例缓存（用于测试或重新加载配置）"""
    logger.info("Clearing singleton cache")
    get_memory_manager.cache_clear()
    get_tool_executor.cache_clear()
    get_context_loader.cache_clear()
    
    # 重置 LLM 客户端
    from .llm.client import reset_clients
    reset_clients()


# ==================== 健康检查 ====================

async def health_check() -> dict:
    """检查所有依赖组件的健康状态"""
    health_status = {
        "status": "healthy",
        "components": {},
        "langchain_version": "1.0+",
    }
    
    try:
        # 检查 LLM 客户端
        llm = get_llm_client()
        health_status["components"]["llm"] = {
            "status": "ok",
            "model": llm.model_name,
            "provider": "configured" if settings.OPENAI_API_KEY else "not_configured"
        }
    except Exception as e:
        health_status["components"]["llm"] = {"status": "error", "error": str(e)}
        health_status["status"] = "degraded"
    
    try:
        # 检查 MCP 注册表
        servers = await mcp_registry.list_servers()
        health_status["components"]["mcp"] = {
            "status": "ok",
            "servers_count": len(servers)
        }
    except Exception as e:
        health_status["components"]["mcp"] = {"status": "error", "error": str(e)}
        health_status["status"] = "degraded"
    
    try:
        # 检查内存管理器
        memory = get_memory_manager()
        health_status["components"]["memory"] = {
            "status": "ok",
            "type": memory.memory_type,
        }
    except Exception as e:
        health_status["components"]["memory"] = {"status": "error", "error": str(e)}
        health_status["status"] = "degraded"
    
    try:
        # 检查上下文加载器
        context_loader = get_context_loader()
        health_status["components"]["context_loader"] = {
            "status": "ok",
            "workspace_root": str(context_loader.workspace_root),
        }
    except Exception as e:
        health_status["components"]["context_loader"] = {"status": "error", "error": str(e)}
        health_status["status"] = "degraded"
    
    return health_status

# -*- coding: utf-8 -*-
"""
依赖注入 - 统一管理组件生命周期

LangChain 1.0 架构:
- AgentEngine 是核心入口，内部使用 LangChainAgent
- 单例模式管理共享资源（MemoryManager, ToolExecutor, ContextLoader）
- 每次请求创建新的 AgentEngine 实例（复用单例依赖）
"""
from typing import Optional

from .core.memory import MemoryManager
from .core.tool_executor import ToolExecutor
from .core.context_loader import ContextLoader
from .core.agent import AgentEngine
from .mcp import mcp_registry
from .llm.client import get_llm_client
from .config import settings
from loguru import logger


# ==================== 单例组件 ====================

# 使用全局变量存储单例，而不是 lru_cache
_memory_manager_instance: Optional[MemoryManager] = None
_tool_executor_instance: Optional[ToolExecutor] = None
_context_loader_instance: Optional[ContextLoader] = None


def get_memory_manager() -> MemoryManager:
    """获取内存管理器实例（单例）"""
    global _memory_manager_instance
    if _memory_manager_instance is None:
        logger.debug("Creating MemoryManager instance")
        _memory_manager_instance = MemoryManager()
    return _memory_manager_instance


def get_tool_executor() -> ToolExecutor:
    """获取工具执行器实例（单例）"""
    global _tool_executor_instance
    if _tool_executor_instance is None:
        logger.debug("Creating ToolExecutor instance")
        _tool_executor_instance = ToolExecutor(mcp_registry)
    return _tool_executor_instance


def get_context_loader() -> ContextLoader:
    """获取上下文加载器实例（单例）"""
    global _context_loader_instance
    if _context_loader_instance is None:
        logger.debug("Creating ContextLoader instance")
        _context_loader_instance = ContextLoader()
    return _context_loader_instance


# ==================== 每次请求创建 ====================

def get_agent_engine() -> AgentEngine:
    """
    获取 Agent 引擎实例
    
    基于 LangChain 1.0 create_agent 构建
    
    注意：每次请求都会创建新的 AgentEngine 实例，
    但会复用单例的依赖组件
    
    Returns:
        AgentEngine 实例
    """
    logger.debug("Creating AgentEngine instance")
    
    return AgentEngine(
        memory_manager=get_memory_manager(),
        tool_executor=get_tool_executor(),
        context_loader=get_context_loader(),
        enable_summarization=True,
        enable_pii_filter=False,
        enable_human_in_loop=False,
        enable_todo_list=False,
    )


# ==================== 清理函数 ====================

def clear_singleton_cache():
    """清理单例缓存（用于测试或重新加载配置）"""
    global _memory_manager_instance, _tool_executor_instance, _context_loader_instance
    
    logger.info("Clearing singleton cache")
    _memory_manager_instance = None
    _tool_executor_instance = None
    _context_loader_instance = None
    
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

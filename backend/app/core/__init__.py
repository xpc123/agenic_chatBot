"""
核心模块导出

LangChain 1.0 架构:
- AgentEngine: 主入口，协调上下文加载、RAG、Agent 执行
- LangChainAgent: 基于 create_agent 的 Agent 实现
- MemoryManager: 会话记忆管理
- ToolExecutor: MCP 工具执行器
"""
from .agent import AgentEngine
from .langchain_agent import LangChainAgent, AgentContext
from .memory import MemoryManager
from .executor import ToolExecutor
from .context_loader import ContextLoader
from .tools import (
    calculator,
    get_current_time,
    get_current_date,
    search_web,
    get_builtin_tools,
    get_basic_tools,
)

__all__ = [
    # 主要组件
    "AgentEngine",
    "LangChainAgent",
    "AgentContext",
    "MemoryManager",
    "ToolExecutor",
    "ContextLoader",
    # 工具
    "calculator",
    "get_current_time",
    "get_current_date",
    "search_web",
    "get_builtin_tools",
    "get_basic_tools",
]

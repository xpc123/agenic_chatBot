# -*- coding: utf-8 -*-
"""
核心模块导出

LangChain 1.0 架构:
- Orchestrator: 业务协调器（主入口）
- ExecutorAgent: 基于 create_agent 的 Agent 实现
- MemoryManager: 会话记忆管理
- ToolExecutor: MCP 工具执行器
"""
from .orchestrator import Orchestrator
from .agent_engine import ExecutorAgent, AgentContext
from .memory import MemoryManager
from .tool_executor import ToolExecutor
from .context_loader import ContextLoader
from .tools import (
    calculator,
    get_current_time,
    get_current_date,
    search_web,
    get_builtin_tools,
    get_basic_tools,
)

# 向后兼容别名
AgentEngine = Orchestrator

__all__ = [
    # 主要组件
    "Orchestrator",
    "AgentEngine",  # 向后兼容别名
    "ExecutorAgent",
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

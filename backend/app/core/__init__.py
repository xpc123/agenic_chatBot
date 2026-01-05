# -*- coding: utf-8 -*-
"""
核心模块导出

LangChain 1.0 架构:
- Orchestrator: 业务协调器（主入口）
- ExecutorAgent: 基于 create_agent 的 Agent 实现
- MemoryManager: 会话记忆管理
- ToolExecutor: MCP 工具执行器

Cursor 风格增强:
- CursorStyleOrchestrator: Cursor 级别的编排器
- IntentRecognizer: 深度意图识别
- AgentLoop: 自主执行循环
- ToolOrchestrator: 智能工具编排
- ContextManager: 上下文工程
- UserPreferenceManager: 用户偏好学习
"""
from .orchestrator import Orchestrator
from .agent_engine import ExecutorAgent, AgentContext
from .memory import MemoryManager
from .tool_executor import ToolExecutor
from .context_loader import ContextLoader
from .tools import (
    get_current_time,
    get_builtin_tools,
    get_basic_tools,
)

# Cursor 风格增强组件
from .cursor_style_orchestrator import CursorStyleOrchestrator, get_orchestrator
from .intent_recognizer import IntentRecognizer, Intent, TaskType, get_intent_recognizer
from .agent_loop import AgentLoop, ProgressUpdate, get_loop_manager
from .tool_orchestrator import ToolOrchestrator, get_tool_orchestrator
from .context_manager import ContextManager, build_context
from .user_preferences import UserPreferenceManager, get_preference_manager
from .skills import SkillsManager, Skill, get_skills_manager
from .planner import AgentPlanner

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
    
    # Cursor 风格增强
    "CursorStyleOrchestrator",
    "get_orchestrator",
    "IntentRecognizer",
    "Intent",
    "TaskType",
    "get_intent_recognizer",
    "AgentLoop",
    "ProgressUpdate",
    "get_loop_manager",
    "ToolOrchestrator",
    "get_tool_orchestrator",
    "ContextManager",
    "build_context",
    "UserPreferenceManager",
    "get_preference_manager",
    "SkillsManager",
    "Skill",
    "get_skills_manager",
    "AgentPlanner",
    
    # 工具
    "get_current_time",
    "get_builtin_tools",
    "get_basic_tools",
]

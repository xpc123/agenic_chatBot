# -*- coding: utf-8 -*-
"""
Agentic ChatBot SDK
===================

通用 AI 助手 SDK，可嵌入任何 Python 应用。

快速开始::

    from agentic_sdk import ChatBot
    
    # 创建实例
    bot = ChatBot()
    
    # 同步对话
    response = bot.chat("你好")
    print(response.text)
    
    # 流式对话
    for chunk in bot.chat_stream("讲个故事"):
        print(chunk.text, end="", flush=True)

高级用法::

    from agentic_sdk import ChatBot, ChatConfig
    
    # 自定义配置
    config = ChatConfig(
        enable_rag=True,
        enable_memory=True,
        enable_skills=True,
    )
    bot = ChatBot(config)
    
    # 添加自定义工具
    @bot.tool
    def get_weather(city: str) -> str:
        return f"{city}天气：晴，25°C"
    
    # 加载知识库
    bot.load_documents(["./docs/manual.pdf"])
    
    # 对话
    response = bot.chat("北京天气怎么样？")
"""

__version__ = "0.1.0"
__author__ = "Agentic ChatBot Team"

from .chatbot import ChatBot
from .config import ChatConfig, LLMConfig, RAGConfig, MemoryConfig, SkillsConfig, MCPConfig
from .types import ChatResponse, ChatChunk, ToolCall, MessageRole
from .settings import SettingsManager, IndexingStatus, SkillInfo, RuleInfo, MCPServerInfo
from .remote_client import RemoteClient

__all__ = [
    # 核心
    "ChatBot",
    "ChatConfig",
    "RemoteClient",
    # 配置
    "LLMConfig",
    "RAGConfig", 
    "MemoryConfig",
    "SkillsConfig",
    "MCPConfig",
    # 类型
    "ChatResponse",
    "ChatChunk",
    "ToolCall",
    "MessageRole",
    # 设置管理（对应 Settings UI）
    "SettingsManager",
    "IndexingStatus",
    "SkillInfo",
    "RuleInfo",
    "MCPServerInfo",
    # 服务器（可选）
    "create_server",
    "run_server",
    # UI（可选）
    "create_ui",
    "launch_ui",
]


# 延迟导入可选组件
def create_server(config=None):
    """创建 HTTP API 服务器"""
    from .server import ChatBotServer
    return ChatBotServer(config)


def run_server(host="0.0.0.0", port=8000, config=None):
    """运行 HTTP API 服务器"""
    from .server import run_server as _run
    _run(host=host, port=port, config=config)


def create_ui(bot=None, config=None, **kwargs):
    """创建 Gradio UI"""
    from .ui import create_ui as _create
    return _create(bot, config, **kwargs)


def launch_ui(host="0.0.0.0", port=7860, config=None, **kwargs):
    """启动 Gradio UI"""
    from .ui import launch_ui as _launch
    _launch(host=host, port=port, config=config, **kwargs)


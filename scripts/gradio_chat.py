# -*- coding: utf-8 -*-
"""
Gradio 聊天界面
简单快速的 Web UI，无需 npm/Node.js
"""
import sys
import os
from pathlib import Path

# 获取项目根目录
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# 加载 backend/.env 环境变量
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / 'backend' / '.env')

# 添加 backend 路径
sys.path.insert(0, str(PROJECT_ROOT / 'backend'))

import gradio as gr
import asyncio
from loguru import logger

# 导入核心组件
from app.core import AgentEngine, MemoryManager, ToolExecutor
from app.core.context_loader import ContextLoader
from app.mcp import mcp_registry


class GradioChatBot:
    """Gradio 聊天机器人"""
    
    def __init__(self):
        self.agent = None
        self.memory = None
        self.session_id = "gradio-session"
        self._initialized = False
        # 创建持久的事件循环
        self._loop = asyncio.new_event_loop()
        
    def _run_async(self, coro):
        """在持久事件循环中运行协程"""
        return self._loop.run_until_complete(coro)
        
    def initialize(self):
        """初始化 Agent（同步）"""
        if self._initialized:
            return
            
        logger.info("Initializing ChatBot...")
        
        # 创建核心组件
        self.memory = MemoryManager()
        tool_executor = ToolExecutor(mcp_registry)
        context_loader = ContextLoader()
        
        # 创建 Agent
        self.agent = AgentEngine(
            memory_manager=self.memory,
            tool_executor=tool_executor,
            context_loader=context_loader,
            enable_summarization=False,
        )
        
        self._initialized = True
        logger.info("✅ ChatBot initialized!")
        
    async def _chat_async(self, message: str) -> str:
        """异步处理消息"""
        try:
            # agent.chat 返回 AsyncGenerator，需要迭代收集结果
            full_response = ""
            async for chunk in self.agent.chat(
                message=message,
                session_id=self.session_id
            ):
                chunk_type = chunk.get("type", "")
                if chunk_type == "text":
                    full_response = chunk.get("content", "")  # 取最后一个完整响应
                elif chunk_type == "tool_call":
                    meta = chunk.get("metadata", {})
                    tool_name = meta.get("tool", "unknown")
                    tool_args = meta.get("args", {})
                    logger.info(f"🔧 Tool call: {tool_name}, args: {tool_args}")
                elif chunk_type == "tool_result":
                    result_content = chunk.get("metadata", {}).get("result", "")
                    logger.info(f"✅ Tool result: {result_content[:200]}")
                elif chunk_type == "error":
                    full_response = chunk.get("content", "Error")
            
            return full_response if full_response else "（AI 正在思考中...）"
        except Exception as e:
            logger.error(f"Chat error: {e}")
            import traceback
            traceback.print_exc()
            return f"❌ 错误: {str(e)}"
    
    def chat(self, message: str, history: list) -> str:
        """同步聊天接口（Gradio 调用）"""
        # 确保初始化
        if not self._initialized:
            self.initialize()
        
        # 在持久事件循环中运行异步聊天
        return self._run_async(self._chat_async(message))


def create_demo():
    """创建 Gradio 界面"""
    bot = GradioChatBot()
    
    # 使用 ChatInterface
    demo = gr.ChatInterface(
        fn=bot.chat,
        title="🤖 Agentic ChatBot",
        description="""
        **基于 LangChain 1.0 的智能助手**
        
        功能特性：
        - 🧮 数学计算
        - ⏰ 时间查询  
        - 🔍 网页搜索
        - 📚 RAG 知识检索
        """,
        examples=[
            "你好，请介绍一下你自己",
            "计算 (123 + 456) * 789",
            "现在几点了？",
            "今天是几号？",
        ],
    )
    
    return demo


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║           🤖 Agentic ChatBot - Gradio UI                     ║
╠══════════════════════════════════════════════════════════════╣
║  ✨ 纯 Python 实现，无需 npm/Node.js                         ║
║  📍 启动后访问显示的 URL                                     ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    demo = create_demo()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7861,  # 使用 7861 端口
        share=False,  # 设置为 True 可生成公网链接
        show_error=True,
    )

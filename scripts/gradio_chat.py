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
from app.core.agent_engine import init_tool_registry, get_tool_registry
from app.mcp import mcp_registry


# ==================== 初始化工具注册表 ====================

def setup_tool_registry():
    """初始化全局工具注册表"""
    api_config_path = str(PROJECT_ROOT / 'backend' / 'config' / 'api_tools.json')
    
    registry = init_tool_registry(
        load_builtin=True,
        load_extended=True,
        api_config_path=api_config_path if os.path.exists(api_config_path) else None,
    )
    
    logger.info(f"🔧 工具注册表初始化完成，共 {len(registry.get_tool_names())} 个工具")
    return registry


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
    
    def upload_document(self, file) -> str:
        """上传文档到知识库"""
        if not self._initialized:
            self.initialize()
        
        if file is None:
            return "❌ 请选择文件"
        
        try:
            from app.rag.retriever import retriever
            
            # 上传文档
            doc = self._run_async(retriever.add_document(file.name))
            return f"✅ 文档上传成功！\n📄 文件名: {doc.filename}\n📊 分块数: {len(doc.chunks) if hasattr(doc, 'chunks') else 'N/A'}"
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return f"❌ 上传失败: {str(e)}"
    
    def clear_session(self) -> str:
        """清空会话历史"""
        try:
            self._run_async(self.memory.clear_session(self.session_id))
            return "✅ 会话已清空"
        except Exception as e:
            return f"❌ 清空失败: {str(e)}"


def create_demo():
    """创建增强版 Gradio 界面"""
    
    # 首先初始化工具注册表
    registry = setup_tool_registry()
    
    bot = GradioChatBot()
    
    # 获取工具列表用于显示
    tool_list = registry.list_tools()
    tool_markdown = "\n".join([
        f"- {'✅' if t['enabled'] else '⏸️'} **{t['name']}**: {t['description'][:30]}..."
        for t in tool_list[:10]  # 最多显示10个
    ])
    if len(tool_list) > 10:
        tool_markdown += f"\n- ... 还有 {len(tool_list) - 10} 个工具"
    
    with gr.Blocks(
        title="🤖 Agentic ChatBot",
    ) as demo:
        gr.Markdown("""
        # 🤖 Agentic ChatBot
        **基于 LangChain 1.0 + Claude Sonnet 4.5 的智能助手**
        
        ---
        """)
        
        with gr.Row():
            # 左侧：主聊天区域
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="对话",
                    height=500,
                )
                
                with gr.Row():
                    msg = gr.Textbox(
                        label="输入消息",
                        placeholder="输入您的问题...",
                        scale=4,
                        show_label=False,
                    )
                    submit_btn = gr.Button("发送", variant="primary", scale=1)
                
                with gr.Row():
                    clear_btn = gr.Button("🗑️ 清空对话", size="sm")
                    
                gr.Examples(
                    examples=[
                        "你好，请介绍一下你自己",
                        "计算 (123 + 456) * 789",
                        "现在几点了？",
                        "今天是星期几？",
                        "用 Python 计算斐波那契数列前10项",
                    ],
                    inputs=msg,
                )
            
            # 右侧：功能面板
            with gr.Column(scale=1):
                gr.Markdown("### 📚 知识库管理")
                
                file_upload = gr.File(
                    label="上传文档",
                    file_types=[".txt", ".pdf", ".md", ".docx"],
                )
                upload_btn = gr.Button("📤 上传到知识库", size="sm")
                upload_status = gr.Textbox(
                    label="上传状态",
                    interactive=False,
                    lines=3,
                )
                
                gr.Markdown("---")
                gr.Markdown("### 🛠️ 可用工具")
                gr.Markdown(tool_markdown if tool_markdown else "暂无工具")
                
                gr.Markdown("---")
                gr.Markdown("### ℹ️ 系统信息")
                gr.Markdown(f"""
                - **模型**: Claude Sonnet 4.5
                - **框架**: LangChain 1.0
                - **向量库**: FAISS
                - **工具数量**: {len(tool_list)}
                - **会话ID**: `{bot.session_id[:8]}...`
                """)
        
        # 事件处理 - Gradio 6.x 使用新的消息格式
        def respond(message, history):
            response = bot.chat(message, history)
            # Gradio 6.x Chatbot 需要 messages 格式
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": response})
            return "", history
        
        submit_btn.click(respond, [msg, chatbot], [msg, chatbot])
        msg.submit(respond, [msg, chatbot], [msg, chatbot])
        clear_btn.click(lambda: [], None, chatbot)
        upload_btn.click(bot.upload_document, file_upload, upload_status)
    
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
        server_port=7861,
        share=False,
        show_error=True,
    )

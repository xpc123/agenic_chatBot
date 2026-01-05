# -*- coding: utf-8 -*-
"""
Gradio 聊天界面 V2 - Cursor 风格

使用 CursorStyleOrchestrator，支持：
1. 意图识别展示
2. 进度追踪
3. 工具调用可视化
4. 用户偏好
5. 流式输出
"""
import sys
import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

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
from app.core.cursor_style_orchestrator import CursorStyleOrchestrator
from app.core.intent_recognizer import IntentRecognizer, TaskType
from app.core.skills import get_skills_manager
from app.core.practical_tools import get_practical_tools
from app.llm import get_llm_client


# ==================== 常量 ====================

HISTORY_DIR = PROJECT_ROOT / 'data' / 'chat_history_v2'
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


# ==================== 全局状态 ====================

class ChatState:
    """聊天状态管理"""
    
    def __init__(self):
        self.orchestrator: Optional[CursorStyleOrchestrator] = None
        self.session_id: str = str(uuid.uuid4())[:8]
        self.user_id: str = "gradio_user"
        self.history: List[Dict] = []
        self.current_intent: Optional[Dict] = None
        self.current_tools: List[str] = []
        self._loop = asyncio.new_event_loop()
        
    def initialize(self):
        """初始化编排器"""
        if self.orchestrator is not None:
            return
            
        logger.info("Initializing CursorStyleOrchestrator...")
        
        try:
            llm_client = get_llm_client()
            tools = get_practical_tools()
            
            self.orchestrator = CursorStyleOrchestrator(
                llm_client=llm_client,
                tools=tools,
                enable_rag=True,
                enable_skills=True,
                enable_memory=True,
                enable_preferences=True,
                max_context_tokens=8000,
            )
            
            logger.info("✅ CursorStyleOrchestrator initialized!")
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            raise
    
    def run_async(self, coro):
        """运行异步协程"""
        return self._loop.run_until_complete(coro)
    
    def new_session(self):
        """创建新会话"""
        self.session_id = str(uuid.uuid4())[:8]
        self.history = []
        self.current_intent = None
        self.current_tools = []
        if self.orchestrator:
            self.orchestrator.clear_session(self.session_id)


# 全局状态
state = ChatState()


# ==================== 聊天函数 ====================

def chat(message: str, history: List[Tuple[str, str]]) -> Tuple[List[Tuple[str, str]], str, str, str]:
    """
    聊天处理函数
    
    Returns:
        (history, intent_info, tool_info, progress_info)
    """
    if not message.strip():
        return history, "", "", ""
    
    # 初始化
    state.initialize()
    
    # 运行异步聊天
    async def async_chat():
        intent_info = ""
        tool_info = ""
        progress_info = ""
        response_text = ""
        tools_used = []
        
        async for chunk in state.orchestrator.chat_stream(
            message=message,
            session_id=state.session_id,
            user_id=state.user_id,
        ):
            chunk_type = chunk.type
            
            if chunk_type == "thinking":
                progress_info = f"💭 {chunk.content}"
                
            elif chunk_type == "tool_call":
                tool_name = chunk.metadata.get("tool", "") if chunk.metadata else ""
                if tool_name:
                    tools_used.append(tool_name)
                tool_info = f"🔧 调用: {', '.join(tools_used)}"
                progress_info = f"⚙️ {chunk.content}"
                
            elif chunk_type == "tool_result":
                tool_info = f"✅ 完成: {', '.join(tools_used)}"
                
            elif chunk_type == "progress":
                step = chunk.metadata.get("step", 0) if chunk.metadata else 0
                total = chunk.metadata.get("total", 0) if chunk.metadata else 0
                progress_info = f"📊 步骤 {step}/{total}: {chunk.content}"
                
            elif chunk_type == "text":
                response_text = chunk.content
                
            elif chunk_type == "complete":
                if chunk.metadata:
                    intent_data = chunk.metadata.get("intent", {})
                    if intent_data:
                        intent_info = format_intent(intent_data)
                    duration = chunk.metadata.get("duration_ms", 0)
                    progress_info = f"✅ 完成 (耗时: {duration}ms)"
                
            elif chunk_type == "error":
                response_text = f"❌ {chunk.content}"
        
        return response_text, intent_info, tool_info, progress_info
    
    try:
        response, intent_info, tool_info, progress_info = state.run_async(async_chat())
    except Exception as e:
        logger.error(f"Chat error: {e}")
        import traceback
        traceback.print_exc()
        response = f"❌ 错误: {str(e)}"
        intent_info = ""
        tool_info = ""
        progress_info = ""
    
    # 更新历史
    history.append((message, response or "（无响应）"))
    
    return history, intent_info, tool_info, progress_info


def format_intent(intent_data: Dict) -> str:
    """格式化意图信息"""
    if not intent_data:
        return ""
    
    lines = [
        "### 🎯 意图分析",
        f"**表层意图**: {intent_data.get('surface_intent', 'N/A')}",
        f"**深层意图**: {intent_data.get('deep_intent', 'N/A')}",
        f"**任务类型**: {intent_data.get('task_type', 'N/A')}",
        f"**复杂度**: {intent_data.get('complexity', 'N/A')}",
        f"**多步骤**: {'是' if intent_data.get('is_multi_step') else '否'}",
    ]
    
    capabilities = intent_data.get('required_capabilities', [])
    if capabilities:
        lines.append(f"**需要能力**: {', '.join(capabilities)}")
    
    tools = intent_data.get('suggested_tools', [])
    if tools:
        lines.append(f"**推荐工具**: {', '.join(tools)}")
    
    return "\n".join(lines)


def new_session():
    """创建新会话"""
    state.new_session()
    return [], "", "", ""


def get_skills_list() -> str:
    """获取技能列表"""
    try:
        manager = get_skills_manager()
        skills = manager.list_skills()
        
        lines = ["### 🎓 可用技能\n"]
        for skill in skills:
            triggers = ", ".join(skill.triggers[:3])
            lines.append(f"**{skill.name}**")
            lines.append(f"- {skill.description}")
            lines.append(f"- 触发词: `{triggers}`")
            lines.append("")
        
        return "\n".join(lines)
    except Exception as e:
        return f"加载技能失败: {e}"


def get_tools_list() -> str:
    """获取工具列表"""
    try:
        tools = get_practical_tools()
        
        lines = ["### 🔧 可用工具\n"]
        for tool in tools:
            name = tool.__name__
            doc = (tool.__doc__ or "").split("\n")[0]
            lines.append(f"- **{name}**: {doc}")
        
        return "\n".join(lines)
    except Exception as e:
        return f"加载工具失败: {e}"


# ==================== 创建界面 ====================

def create_demo():
    """创建 Gradio 界面"""
    
    # 预加载信息
    skills_info = get_skills_list()
    tools_info = get_tools_list()
    
    with gr.Blocks(
        title="🤖 Agentic ChatBot v2 - Cursor Style",
        theme=gr.themes.Soft(primary_hue="indigo"),
    ) as demo:
        
        gr.Markdown("""
        # 🤖 Agentic ChatBot v2 - Cursor Style
        
        **使用 CursorStyleOrchestrator 的智能助手** | 支持意图识别、工具编排、用户偏好学习
        """)
        
        with gr.Row():
            # 左侧：技能和工具
            with gr.Column(scale=1, min_width=250):
                gr.Markdown("### 📊 系统状态")
                
                intent_display = gr.Markdown(
                    value="*等待输入...*",
                    label="意图分析",
                )
                
                tool_display = gr.Textbox(
                    label="工具状态",
                    value="",
                    interactive=False,
                    lines=2,
                )
                
                progress_display = gr.Textbox(
                    label="执行进度",
                    value="",
                    interactive=False,
                    lines=1,
                )
                
                gr.Markdown("---")
                
                with gr.Accordion("🎓 可用技能", open=False):
                    gr.Markdown(skills_info)
                
                with gr.Accordion("🔧 可用工具", open=False):
                    gr.Markdown(tools_info)
            
            # 中间：聊天区域
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="对话",
                    height=500,
                    show_copy_button=True,
                )
                
                with gr.Row():
                    msg = gr.Textbox(
                        placeholder="输入您的问题... (Enter 发送)",
                        show_label=False,
                        scale=5,
                        lines=2,
                    )
                    submit_btn = gr.Button("发送 ➤", variant="primary", scale=1)
                
                with gr.Row():
                    new_session_btn = gr.Button("🆕 新会话", size="sm")
                    clear_btn = gr.Button("🗑️ 清空", size="sm")
                
                gr.Examples(
                    examples=[
                        "你好，介绍一下你自己",
                        "帮我分析一下当前目录下有哪些文件",
                        "用 Python 计算斐波那契数列的前 20 项",
                        "获取系统环境信息",
                        "首先查看进程列表，然后分析资源使用情况",
                    ],
                    inputs=msg,
                    label="示例问题",
                )
        
        # ========== 事件绑定 ==========
        
        # 发送消息
        submit_btn.click(
            chat,
            inputs=[msg, chatbot],
            outputs=[chatbot, intent_display, tool_display, progress_display],
        ).then(
            lambda: "",
            outputs=msg,
        )
        
        msg.submit(
            chat,
            inputs=[msg, chatbot],
            outputs=[chatbot, intent_display, tool_display, progress_display],
        ).then(
            lambda: "",
            outputs=msg,
        )
        
        # 新会话
        new_session_btn.click(
            new_session,
            outputs=[chatbot, intent_display, tool_display, progress_display],
        )
        
        # 清空
        clear_btn.click(
            lambda: ([], "", "", ""),
            outputs=[chatbot, intent_display, tool_display, progress_display],
        )
    
    return demo


# ==================== 主入口 ====================

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════╗
║         🤖 Agentic ChatBot v2 - Cursor Style                   ║
╠════════════════════════════════════════════════════════════════╣
║  ✨ CursorStyleOrchestrator | 意图识别 | 智能工具编排          ║
║  📍 启动后访问: http://localhost:7862                          ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    demo = create_demo()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7862,
        share=False,
        show_error=True,
    )


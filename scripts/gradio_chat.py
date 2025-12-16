# -*- coding: utf-8 -*-
"""
Gradio 聊天界面 - Agentic ChatBot

功能:
- 流式输出
- 工具调用可视化
- 多会话支持
- 历史持久化 + 导出
- 自定义头像
- 代码语法高亮
"""
import sys
import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Generator

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


# ==================== 常量定义 ====================

HISTORY_DIR = PROJECT_ROOT / 'data' / 'chat_history'
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

# 自定义头像
USER_AVATAR = "👤"
BOT_AVATAR = "🤖"

# CSS 样式
CUSTOM_CSS = """
/* 工具调用面板 */
.tool-panel {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 10px;
    padding: 10px;
    margin: 5px 0;
    color: white;
}

.tool-call {
    background: rgba(255,255,255,0.1);
    border-radius: 8px;
    padding: 8px 12px;
    margin: 4px 0;
    font-family: monospace;
}

.tool-result {
    background: rgba(0,255,0,0.1);
    border-left: 3px solid #4CAF50;
    padding: 8px 12px;
    margin: 4px 0;
}

/* 思考中动画 */
.thinking {
    display: inline-block;
    animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

/* 消息时间戳 */
.timestamp {
    font-size: 0.75em;
    color: #888;
    margin-top: 4px;
}

/* 会话列表 */
.session-item {
    padding: 8px 12px;
    margin: 4px 0;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.2s;
}

.session-item:hover {
    background: rgba(0,0,0,0.05);
}

.session-active {
    background: rgba(102, 126, 234, 0.1);
    border-left: 3px solid #667eea;
}
"""


# ==================== 会话管理器 ====================

class SessionManager:
    """会话管理器 - 支持多会话和持久化"""
    
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
        self.current_session_id: str = ""
        self._load_sessions()
    
    def _load_sessions(self):
        """从磁盘加载会话列表"""
        try:
            for file in HISTORY_DIR.glob("*.json"):
                session_id = file.stem
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sessions[session_id] = {
                        "name": data.get("name", f"会话 {session_id[:8]}"),
                        "created_at": data.get("created_at", ""),
                        "messages": data.get("messages", []),
                    }
            logger.info(f"📂 加载了 {len(self.sessions)} 个历史会话")
        except Exception as e:
            logger.error(f"加载会话失败: {e}")
    
    def create_session(self, name: str = "") -> str:
        """创建新会话"""
        session_id = str(uuid.uuid4())[:8]
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.sessions[session_id] = {
            "name": name or f"会话 {now}",
            "created_at": now,
            "messages": [],
        }
        self.current_session_id = session_id
        self._save_session(session_id)
        logger.info(f"📝 创建新会话: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def get_current_session(self) -> Optional[Dict]:
        """获取当前会话"""
        if not self.current_session_id:
            self.create_session()
        return self.sessions.get(self.current_session_id)
    
    def add_message(self, role: str, content: str, metadata: Dict = None):
        """添加消息到当前会话"""
        session = self.get_current_session()
        if session:
            session["messages"].append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
            })
            self._save_session(self.current_session_id)
    
    def get_messages(self) -> List[Dict]:
        """获取当前会话消息"""
        session = self.get_current_session()
        return session["messages"] if session else []
    
    def clear_current_session(self):
        """清空当前会话"""
        session = self.get_current_session()
        if session:
            session["messages"] = []
            self._save_session(self.current_session_id)
    
    def delete_session(self, session_id: str):
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            file_path = HISTORY_DIR / f"{session_id}.json"
            if file_path.exists():
                file_path.unlink()
            logger.info(f"🗑️ 删除会话: {session_id}")
    
    def switch_session(self, session_id: str) -> bool:
        """切换会话"""
        if session_id in self.sessions:
            self.current_session_id = session_id
            return True
        return False
    
    def list_sessions(self) -> List[Dict]:
        """列出所有会话"""
        return [
            {"id": sid, **info}
            for sid, info in sorted(
                self.sessions.items(),
                key=lambda x: x[1].get("created_at", ""),
                reverse=True
            )
        ]
    
    def _save_session(self, session_id: str):
        """保存会话到磁盘"""
        try:
            session = self.sessions.get(session_id)
            if session:
                file_path = HISTORY_DIR / f"{session_id}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(session, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存会话失败: {e}")
    
    def export_markdown(self, session_id: str = None) -> str:
        """导出会话为 Markdown"""
        sid = session_id or self.current_session_id
        session = self.sessions.get(sid)
        if not session:
            return "# 无会话记录"
        
        lines = [
            f"# {session['name']}",
            f"*创建时间: {session['created_at']}*",
            "",
            "---",
            "",
        ]
        
        for msg in session["messages"]:
            role = "👤 用户" if msg["role"] == "user" else "🤖 助手"
            timestamp = msg.get("timestamp", "")[:19].replace("T", " ")
            lines.append(f"### {role} ({timestamp})")
            lines.append("")
            lines.append(msg["content"])
            lines.append("")
        
        return "\n".join(lines)


# ==================== 增强版聊天机器人 ====================

class EnhancedChatBot:
    """增强版 Gradio 聊天机器人"""
    
    def __init__(self):
        self.agent = None
        self.memory = None
        self.session_manager = SessionManager()
        self._initialized = False
        self._loop = asyncio.new_event_loop()
        
        # 工具调用状态
        self.current_tool_calls: List[Dict] = []
    
    def _run_async(self, coro):
        """在持久事件循环中运行协程"""
        return self._loop.run_until_complete(coro)
    
    def initialize(self):
        """初始化 Agent"""
        if self._initialized:
            return
        
        logger.info("Initializing Enhanced ChatBot...")
        
        self.memory = MemoryManager()
        tool_executor = ToolExecutor(mcp_registry)
        context_loader = ContextLoader()
        
        self.agent = AgentEngine(
            memory_manager=self.memory,
            tool_executor=tool_executor,
            context_loader=context_loader,
            enable_summarization=False,
        )
        
        self._initialized = True
        logger.info("✅ Enhanced ChatBot initialized!")
    
    def _format_tool_call(self, tool_name: str, args: Dict) -> str:
        """格式化工具调用显示"""
        args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
        return f"🔧 **{tool_name}**({args_str})"
    
    def _format_tool_result(self, result: str) -> str:
        """格式化工具结果显示"""
        # 截断过长结果
        if len(result) > 500:
            result = result[:500] + "..."
        return f"✅ {result}"
    
    async def _stream_chat(self, message: str) -> Generator:
        """流式聊天 - 生成器"""
        if not self._initialized:
            self.initialize()
        
        session_id = self.session_manager.current_session_id
        self.current_tool_calls = []
        
        try:
            full_response = ""
            tool_info = ""
            
            async for chunk in self.agent.chat(
                message=message,
                session_id=session_id
            ):
                chunk_type = chunk.get("type", "")
                
                if chunk_type == "tool_call":
                    meta = chunk.get("metadata", {})
                    tool_name = meta.get("tool", "unknown")
                    tool_args = meta.get("args", {})
                    
                    tool_display = self._format_tool_call(tool_name, tool_args)
                    self.current_tool_calls.append({
                        "name": tool_name,
                        "args": tool_args,
                        "display": tool_display,
                    })
                    
                    # 更新工具信息
                    tool_info = "\n\n---\n**🔄 正在调用工具...**\n" + "\n".join(
                        t["display"] for t in self.current_tool_calls
                    )
                    yield tool_info, self.current_tool_calls
                
                elif chunk_type == "tool_result":
                    result = chunk.get("metadata", {}).get("result", "")
                    if self.current_tool_calls:
                        self.current_tool_calls[-1]["result"] = result
                        self.current_tool_calls[-1]["display"] += f"\n  → {self._format_tool_result(result)}"
                    
                    tool_info = "\n\n---\n**✅ 工具调用完成**\n" + "\n".join(
                        t["display"] for t in self.current_tool_calls
                    )
                    yield tool_info, self.current_tool_calls
                
                elif chunk_type == "text":
                    full_response = chunk.get("content", "")
                    # 组合工具信息和响应
                    combined = full_response
                    if self.current_tool_calls:
                        combined += "\n\n---\n<details><summary>🔧 工具调用详情</summary>\n\n"
                        combined += "\n".join(t["display"] for t in self.current_tool_calls)
                        combined += "\n</details>"
                    yield combined, self.current_tool_calls
                
                elif chunk_type == "error":
                    error_msg = chunk.get("content", "Unknown error")
                    yield f"❌ 错误: {error_msg}", []
            
            # 保存消息到会话
            self.session_manager.add_message("user", message)
            self.session_manager.add_message("assistant", full_response, {
                "tool_calls": self.current_tool_calls
            })
            
            if not full_response:
                yield "（AI 正在思考中...）", []
                
        except Exception as e:
            logger.error(f"Chat error: {e}")
            import traceback
            traceback.print_exc()
            yield f"❌ 错误: {str(e)}", []
    
    def chat_stream(self, message: str, history: list):
        """流式聊天接口（同步版）"""
        if not message.strip():
            yield history, ""
            return
        
        # 添加用户消息
        history.append({"role": "user", "content": message})
        
        # 添加思考中指示器
        history.append({"role": "assistant", "content": "🤔 *思考中...*"})
        yield history, ""
        
        # 同步收集所有响应
        async def collect_response():
            """收集完整响应"""
            full_response = ""
            tool_calls = []
            
            async for response, tools in self._stream_chat(message):
                full_response = response
                tool_calls = tools
            
            return full_response, tool_calls
        
        try:
            response, tools = self._run_async(collect_response())
        except Exception as e:
            logger.error(f"Chat stream error: {e}")
            import traceback
            traceback.print_exc()
            response = f"❌ 错误: {str(e)}"
            tools = []
        
        # 更新最后一条消息
        if response:
            history[-1] = {"role": "assistant", "content": response}
        else:
            history[-1] = {"role": "assistant", "content": "（AI 无响应，请重试）"}
        
        # 格式化工具调用信息
        tool_display = ""
        if tools:
            tool_display = "\n".join([
                f"• {t['name']}: {t.get('result', 'pending')[:100]}..."
                for t in tools
            ])
        
        yield history, tool_display
    
    def create_new_session(self):
        """创建新会话"""
        self.session_manager.create_session()
        return [], self._get_session_list_html()
    
    def switch_session(self, session_id: str):
        """切换会话"""
        if self.session_manager.switch_session(session_id):
            messages = self.session_manager.get_messages()
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in messages
            ]
            return history, self._get_session_list_html()
        return [], self._get_session_list_html()
    
    def delete_current_session(self):
        """删除当前会话"""
        current_id = self.session_manager.current_session_id
        self.session_manager.delete_session(current_id)
        
        # 创建新会话或切换到其他会话
        sessions = self.session_manager.list_sessions()
        if sessions:
            self.session_manager.switch_session(sessions[0]["id"])
            messages = self.session_manager.get_messages()
            history = [{"role": m["role"], "content": m["content"]} for m in messages]
        else:
            self.session_manager.create_session()
            history = []
        
        return history, self._get_session_list_html()
    
    def clear_current_session(self):
        """清空当前会话"""
        self.session_manager.clear_current_session()
        return [], self._get_session_list_html()
    
    def export_chat(self):
        """导出当前会话"""
        return self.session_manager.export_markdown()
    
    def _get_session_list_html(self) -> str:
        """获取会话列表 HTML"""
        sessions = self.session_manager.list_sessions()
        current_id = self.session_manager.current_session_id
        
        if not sessions:
            return "<p>暂无会话</p>"
        
        lines = []
        for s in sessions[:10]:  # 最多显示10个
            active = "session-active" if s["id"] == current_id else ""
            lines.append(
                f'<div class="session-item {active}" '
                f'onclick="switchSession(\'{s["id"]}\')">'
                f'<strong>{s["name"]}</strong><br>'
                f'<small>{s["created_at"]}</small>'
                f'</div>'
            )
        
        return "\n".join(lines)
    
    def get_session_choices(self):
        """获取会话选择列表"""
        sessions = self.session_manager.list_sessions()
        return [(s["name"], s["id"]) for s in sessions]


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


# ==================== 创建界面 ====================

def create_demo():
    """创建增强版 Gradio 界面"""
    
    # 初始化
    registry = setup_tool_registry()
    bot = EnhancedChatBot()
    
    # 确保有初始会话
    if not bot.session_manager.current_session_id:
        bot.session_manager.create_session()
    
    # 工具列表
    tool_list = registry.list_tools()
    tool_markdown = "\n".join([
        f"- {'✅' if t['enabled'] else '⏸️'} **{t['name']}**"
        for t in tool_list[:15]
    ])
    if len(tool_list) > 15:
        tool_markdown += f"\n- *... 还有 {len(tool_list) - 15} 个*"
    
    # 主题选择
    theme = gr.themes.Soft(
        primary_hue="indigo",
        secondary_hue="purple",
    )
    
    with gr.Blocks(
        title="🤖 Agentic ChatBot v2",
    ) as demo:
        
        # 标题区域
        gr.Markdown("""
        # 🤖 Agentic ChatBot v2
        **基于 LangChain 1.0 + Claude Sonnet 4.5 的智能助手** | *增强版*
        """)
        
        with gr.Row():
            # 左侧边栏 - 会话管理
            with gr.Column(scale=1, min_width=200):
                gr.Markdown("### 📋 会话管理")
                
                new_session_btn = gr.Button("➕ 新建会话", variant="primary", size="sm")
                
                session_dropdown = gr.Dropdown(
                    label="选择会话",
                    choices=bot.get_session_choices(),
                    value=bot.session_manager.current_session_id,
                    interactive=True,
                )
                
                with gr.Row():
                    clear_btn = gr.Button("🗑️ 清空", size="sm")
                    delete_btn = gr.Button("❌ 删除", size="sm", variant="stop")
                
                gr.Markdown("---")
                
                export_btn = gr.Button("📥 导出 Markdown", size="sm")
                export_output = gr.Textbox(
                    label="导出内容",
                    lines=5,
                    visible=False,
                )
                
                gr.Markdown("---")
                gr.Markdown("### 🛠️ 可用工具")
                gr.Markdown(tool_markdown)
                
                gr.Markdown("---")
                gr.Markdown(f"""
                ### ℹ️ 系统信息
                - **模型**: Claude Sonnet 4.5
                - **工具数**: {len(tool_list)}
                - **会话数**: {len(bot.session_manager.sessions)}
                """)
            
            # 中间 - 聊天区域
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="对话",
                    height=550,
                )
                
                with gr.Row():
                    msg = gr.Textbox(
                        label="输入消息",
                        placeholder="输入您的问题... (Enter 发送, Shift+Enter 换行)",
                        scale=5,
                        show_label=False,
                        lines=2,
                    )
                    submit_btn = gr.Button("发送 ➤", variant="primary", scale=1)
                
                gr.Examples(
                    examples=[
                        "你好，请介绍一下你自己",
                        "计算 (123 + 456) * 789 / 2",
                        "现在几点了？今天是星期几？",
                        "用 Python 计算 1 到 100 的和",
                        "获取系统信息",
                    ],
                    inputs=msg,
                )
            
            # 右侧边栏 - 工具调用
            with gr.Column(scale=1, min_width=250):
                gr.Markdown("### 🔧 工具调用状态")
                
                tool_status = gr.Textbox(
                    label="最近工具调用",
                    lines=10,
                    interactive=False,
                    placeholder="工具调用信息将显示在这里...",
                )
                
                gr.Markdown("---")
                gr.Markdown("### 📚 知识库")
                
                file_upload = gr.File(
                    label="上传文档",
                    file_types=[".txt", ".pdf", ".md", ".docx"],
                )
                upload_btn = gr.Button("📤 上传", size="sm")
                upload_status = gr.Textbox(
                    label="状态",
                    lines=2,
                    interactive=False,
                )
        
        # ==================== 事件绑定 ====================
        
        # 发送消息
        submit_btn.click(
            bot.chat_stream,
            inputs=[msg, chatbot],
            outputs=[chatbot, tool_status],
        ).then(
            lambda: "",
            outputs=msg,
        )
        
        msg.submit(
            bot.chat_stream,
            inputs=[msg, chatbot],
            outputs=[chatbot, tool_status],
        ).then(
            lambda: "",
            outputs=msg,
        )
        
        # 新建会话
        new_session_btn.click(
            bot.create_new_session,
            outputs=[chatbot, session_dropdown],
        ).then(
            lambda: gr.update(choices=bot.get_session_choices()),
            outputs=session_dropdown,
        )
        
        # 切换会话
        session_dropdown.change(
            bot.switch_session,
            inputs=session_dropdown,
            outputs=[chatbot, session_dropdown],
        )
        
        # 清空会话
        clear_btn.click(
            bot.clear_current_session,
            outputs=[chatbot, session_dropdown],
        )
        
        # 删除会话
        delete_btn.click(
            bot.delete_current_session,
            outputs=[chatbot, session_dropdown],
        ).then(
            lambda: gr.update(choices=bot.get_session_choices()),
            outputs=session_dropdown,
        )
        
        # 导出
        export_btn.click(
            bot.export_chat,
            outputs=export_output,
        ).then(
            lambda: gr.update(visible=True),
            outputs=export_output,
        )
        
        # 上传文档
        def upload_doc(file):
            if file is None:
                return "❌ 请选择文件"
            try:
                from app.rag.retriever import retriever
                doc = bot._run_async(retriever.add_document(file.name))
                return f"✅ 上传成功: {Path(file.name).name}"
            except Exception as e:
                return f"❌ 上传失败: {e}"
        
        upload_btn.click(upload_doc, file_upload, upload_status)
    
    return demo


# ==================== 主入口 ====================

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════╗
║              🤖 Agentic ChatBot - Gradio UI                    ║
╠════════════════════════════════════════════════════════════════╣
║  ✨ 流式输出 | 工具可视化 | 多会话 | 历史持久化                ║
║  📍 启动后访问: http://localhost:7861                          ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    demo = create_demo()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7861,
        share=False,
        show_error=True,
    )

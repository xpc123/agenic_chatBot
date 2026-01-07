# -*- coding: utf-8 -*-
"""
Gradio SDK UI - 使用统一 SDK 的界面

演示如何使用 agentic_sdk 构建完整 UI：
- 💬 Chat - 智能对话（使用 SDK）
- ⚙️ Settings - 设置管理（使用 SDK）
"""
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# 获取项目根目录
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# 添加路径
sys.path.insert(0, str(PROJECT_ROOT))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / 'backend' / '.env')

import gradio as gr
from loguru import logger

# 使用统一 SDK
from agentic_sdk import ChatBot, ChatConfig


# ==================== 常量 ====================

HISTORY_DIR = PROJECT_ROOT / 'data' / 'chat_history'
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


# ==================== 全局状态 ====================

class AppState:
    """应用状态 - 使用 SDK"""
    
    def __init__(self):
        self.bot: Optional[ChatBot] = None
        self.session_id: str = ""
        self._initialized = False
    
    @property
    def initialized(self) -> bool:
        return self._initialized
    
    def initialize(self):
        """初始化 SDK"""
        if self._initialized:
            return
        
        logger.info("Initializing ChatBot SDK...")
        
        try:
            # 使用嵌入模式（直接调用后端）
            config = ChatConfig.full()
            config.data_dir = HISTORY_DIR
            
            self.bot = ChatBot(config)
            self.session_id = self.bot._get_or_create_session()
            self._initialized = True
            
            logger.info(f"ChatBot SDK initialized, session: {self.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            raise


# 全局状态实例
state = AppState()


# ==================== Chat 功能 ====================

def chat_fn(message: str, history: List[Dict]) -> Tuple[str, List[Dict]]:
    """
    对话处理函数 (Gradio 6.0 格式)
    
    Args:
        message: 用户消息
        history: 对话历史 (messages 格式)
    
    Returns:
        (空字符串, 更新后的历史)
    """
    if not message.strip():
        return "", history
    
    # 确保初始化
    if not state.initialized:
        try:
            state.initialize()
        except Exception as e:
            error_msg = f"❌ 初始化失败: {str(e)}"
            return "", history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": error_msg}
            ]
    
    # 调用 SDK
    try:
        response = state.bot.chat(
            message=message,
            session_id=state.session_id,
        )
        
        reply = response.text
        
        # 添加来源信息
        if response.sources:
            reply += "\n\n📚 参考来源:\n"
            for src in response.sources[:3]:
                reply += f"- {src.get('source', 'unknown')}\n"
        
        return "", history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": reply}
        ]
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        error_msg = f"❌ 错误: {str(e)}"
        return "", history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": error_msg}
        ]


def clear_chat():
    """清空对话"""
    if state.initialized:
        state.bot.clear_conversation(state.session_id)
    return []


def new_session():
    """新建会话"""
    if state.initialized:
        state.session_id = state.bot._get_or_create_session()
    return []


# ==================== Settings 功能 ====================

def get_index_status() -> str:
    """获取索引状态"""
    if not state.initialized:
        return "未初始化"
    
    try:
        status = state.bot.get_index_status(str(PROJECT_ROOT))
        return f"已索引: {status.get('indexed_files', 0)} 个文件"
    except Exception as e:
        return f"获取失败: {e}"


def sync_index(force: bool = False) -> str:
    """同步索引"""
    if not state.initialized:
        state.initialize()
    
    try:
        result = state.bot.sync_index(force=force, workspace=str(PROJECT_ROOT))
        return f"✅ 索引完成: {result.get('indexed_files', 0)} 个文件"
    except Exception as e:
        return f"❌ 索引失败: {e}"


def clear_index() -> str:
    """清除索引"""
    if not state.initialized:
        return "未初始化"
    
    try:
        state.bot.clear_index(str(PROJECT_ROOT))
        return "✅ 索引已清除"
    except Exception as e:
        return f"❌ 清除失败: {e}"


def list_skills() -> List[List[str]]:
    """列出技能"""
    if not state.initialized:
        state.initialize()
    
    try:
        skills = state.bot.list_skills()
        return [[
            s.get('name', ''),
            s.get('description', ''),
            '✅' if s.get('enabled', True) else '❌',
            s.get('id', ''),
        ] for s in skills]
    except Exception as e:
        logger.error(f"List skills error: {e}")
        return []


def toggle_skill(skill_id: str, enable: bool) -> str:
    """切换技能状态"""
    if not state.initialized:
        return "未初始化"
    
    try:
        state.bot.toggle_skill(skill_id, enable)
        return f"✅ 技能 {skill_id} 已{'启用' if enable else '禁用'}"
    except Exception as e:
        return f"❌ 操作失败: {e}"


def get_rules() -> Dict[str, List[str]]:
    """获取规则"""
    if not state.initialized:
        state.initialize()
    
    try:
        return state.bot.get_rules()
    except Exception as e:
        logger.error(f"Get rules error: {e}")
        return {"user_rules": [], "project_rules": []}


def add_rule(content: str, rule_type: str) -> str:
    """添加规则"""
    if not content.strip():
        return "❌ 规则内容不能为空"
    
    if not state.initialized:
        state.initialize()
    
    try:
        state.bot.add_rule(content.strip(), rule_type)
        return f"✅ 规则已添加"
    except Exception as e:
        return f"❌ 添加失败: {e}"


def list_mcp_servers() -> List[List[str]]:
    """列出 MCP 服务器"""
    if not state.initialized:
        state.initialize()
    
    try:
        servers = state.bot.list_mcp_servers()
        return [[
            s.get('name', ''),
            s.get('type', ''),
            s.get('url', '-'),
        ] for s in servers]
    except Exception as e:
        logger.error(f"List MCP servers error: {e}")
        return []


def get_summary() -> str:
    """获取设置摘要"""
    if not state.initialized:
        state.initialize()
    
    try:
        summary = state.bot.get_settings_summary(str(PROJECT_ROOT))
        return f"""📊 设置摘要:
- 已索引文件: {summary.get('indexed_files', 0)}
- 用户规则: {summary.get('user_rules', 0)}
- 项目规则: {summary.get('project_rules', 0)}
- 技能数量: {summary.get('skills', 0)}
- MCP 服务器: {summary.get('mcp_servers', 0)}"""
    except Exception as e:
        return f"❌ 获取失败: {e}"


# ==================== 创建 UI ====================

def create_ui() -> gr.Blocks:
    """创建 Gradio UI"""
    
    with gr.Blocks(title="Agentic ChatBot (SDK)") as app:
        
        gr.Markdown("""
        # 🤖 Agentic ChatBot
        
        **基于统一 SDK 的智能助手** - 支持 RAG、工具调用、技能、记忆等功能
        """)
        
        with gr.Tabs():
            # ==================== Chat Tab ====================
            with gr.Tab("💬 Chat"):
                chatbot = gr.Chatbot(
                    label="对话",
                    height=500,
                )
                
                with gr.Row():
                    msg = gr.Textbox(
                        placeholder="输入消息...",
                        show_label=False,
                        scale=9,
                    )
                    send_btn = gr.Button("发送", variant="primary", scale=1)
                
                with gr.Row():
                    clear_btn = gr.Button("🗑️ 清空对话")
                    new_btn = gr.Button("✨ 新建会话")
                
                # 事件绑定
                msg.submit(chat_fn, [msg, chatbot], [msg, chatbot])
                send_btn.click(chat_fn, [msg, chatbot], [msg, chatbot])
                clear_btn.click(clear_chat, outputs=chatbot)
                new_btn.click(new_session, outputs=chatbot)
            
            # ==================== Settings Tab ====================
            with gr.Tab("⚙️ Settings"):
                
                with gr.Tabs():
                    # --- Indexing ---
                    with gr.Tab("📁 Indexing"):
                        with gr.Row():
                            index_status = gr.Textbox(
                                label="索引状态",
                                value=get_index_status,
                                interactive=False,
                            )
                            refresh_status_btn = gr.Button("🔄 刷新")
                        
                        with gr.Row():
                            sync_btn = gr.Button("📥 同步索引", variant="primary")
                            force_sync_btn = gr.Button("🔄 强制重建")
                            clear_idx_btn = gr.Button("🗑️ 清除索引")
                        
                        index_result = gr.Textbox(label="操作结果", interactive=False)
                        
                        refresh_status_btn.click(get_index_status, outputs=index_status)
                        sync_btn.click(lambda: sync_index(False), outputs=index_result)
                        force_sync_btn.click(lambda: sync_index(True), outputs=index_result)
                        clear_idx_btn.click(clear_index, outputs=index_result)
                    
                    # --- Rules ---
                    with gr.Tab("📜 Rules"):
                        gr.Markdown("### 添加规则")
                        
                        with gr.Row():
                            rule_content = gr.Textbox(
                                label="规则内容",
                                placeholder="输入规则...",
                                scale=3,
                            )
                            rule_type = gr.Radio(
                                choices=["user", "project"],
                                value="user",
                                label="类型",
                                scale=1,
                            )
                            add_rule_btn = gr.Button("➕ 添加", scale=1)
                        
                        rule_result = gr.Textbox(label="操作结果", interactive=False)
                        
                        add_rule_btn.click(
                            add_rule,
                            inputs=[rule_content, rule_type],
                            outputs=rule_result,
                        )
                    
                    # --- Skills ---
                    with gr.Tab("🎯 Skills"):
                        skills_table = gr.Dataframe(
                            headers=["名称", "描述", "状态", "ID"],
                            datatype=["str", "str", "str", "str"],
                            value=list_skills,
                            label="技能列表",
                        )
                        
                        with gr.Row():
                            skill_id_input = gr.Textbox(label="技能 ID", scale=2)
                            enable_toggle = gr.Checkbox(label="启用", value=True)
                            toggle_btn = gr.Button("切换状态", scale=1)
                        
                        skill_result = gr.Textbox(label="操作结果", interactive=False)
                        refresh_skills_btn = gr.Button("🔄 刷新列表")
                        
                        toggle_btn.click(
                            toggle_skill,
                            inputs=[skill_id_input, enable_toggle],
                            outputs=skill_result,
                        )
                        refresh_skills_btn.click(list_skills, outputs=skills_table)
                    
                    # --- MCP ---
                    with gr.Tab("🔧 MCP"):
                        mcp_table = gr.Dataframe(
                            headers=["名称", "类型", "URL"],
                            datatype=["str", "str", "str"],
                            value=list_mcp_servers,
                            label="MCP 服务器",
                        )
                        
                        refresh_mcp_btn = gr.Button("🔄 刷新列表")
                        refresh_mcp_btn.click(list_mcp_servers, outputs=mcp_table)
                    
                    # --- Summary ---
                    with gr.Tab("📊 Summary"):
                        summary_text = gr.Textbox(
                            label="设置摘要",
                            value=get_summary,
                            interactive=False,
                            lines=8,
                        )
                        
                        refresh_summary_btn = gr.Button("🔄 刷新")
                        refresh_summary_btn.click(get_summary, outputs=summary_text)
        
        # 页脚
        gr.Markdown("""
        ---
        **Agentic ChatBot SDK** | [GitHub](https://github.com) | v0.1.0
        
        *使用 `agentic_sdk` 构建，支持嵌入模式和远程模式*
        """)
    
    return app


def main():
    """主入口"""
    print("""
╔═══════════════════════════════════════════════════╗
║         🤖 Agentic ChatBot (SDK Version)          ║
╠═══════════════════════════════════════════════════╣
║  使用统一 SDK 的 Gradio UI                         ║
║  - 嵌入模式: 直接调用后端                           ║
║  - 远程模式: 通过 HTTP API                          ║
╚═══════════════════════════════════════════════════╝
    """)
    
    app = create_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7870,
        share=False,
    )


if __name__ == "__main__":
    main()

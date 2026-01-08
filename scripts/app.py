# -*- coding: utf-8 -*-
"""
Gradio UI - 使用 Agentic SDK 的智能助手界面

功能：
- 💬 Chat - 智能对话（支持 RAG、工具调用）
- ⚙️ Settings - 设置管理（索引、规则、技能、MCP）

使用前请先启动后端服务：
  cd backend && python run.py

启动方式：
  python scripts/app.py
  python scripts/app.py --backend-url http://api.example.com:8000
"""
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import uuid
import os

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

# 使用简化后的 SDK
from agentic_sdk import ChatBot, ConnectionError


# ==================== 常量 ====================

# 后端服务地址（可通过环境变量配置）
DEFAULT_BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


# ==================== 全局状态 ====================

class AppState:
    """应用状态 - 仅支持远程模式"""
    
    def __init__(self):
        self.bot: Optional[ChatBot] = None
        self.session_id: str = ""
        self.backend_url: str = DEFAULT_BACKEND_URL
        self._initialized = False
    
    @property
    def initialized(self) -> bool:
        return self._initialized
    
    def initialize(self, backend_url: Optional[str] = None):
        """初始化 SDK（连接到后端服务）"""
        if self._initialized:
            return
        
        if backend_url:
            self.backend_url = backend_url
        
        logger.info(f"Connecting to backend: {self.backend_url}")
        
        try:
            self.bot = ChatBot(base_url=self.backend_url)
            
            # 检查连接（允许 degraded 状态）
            try:
                health = self.bot.health_check()
                status = health.get("status", "unknown")
                logger.info(f"Backend status: {status}")
            except Exception as e:
                logger.warning(f"Health check warning: {e}")
            
            self.session_id = str(uuid.uuid4())[:8]
            self._initialized = True
            
            logger.info(f"Connected! Session: {self.session_id}")
            
        except ConnectionError as e:
            logger.error(f"Cannot connect to backend: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            raise


# 全局状态实例
state = AppState()


# ==================== Chat 功能 ====================

def chat_fn(message: str, history: List[Dict]) -> Tuple[str, List[Dict]]:
    """
    对话处理函数
    
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
            error_msg = f"❌ 连接失败: {str(e)}\n\n请确保后端服务已启动：\n```\ncd backend && python run.py\n```"
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
        
        # 显示使用的工具
        if response.used_tools:
            reply += f"\n🔧 使用工具: {', '.join(response.used_tools)}"
        
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
        try:
            state.bot.clear_session(state.session_id)
        except Exception as e:
            logger.warning(f"Clear session warning: {e}")
    return []


def new_session():
    """新建会话"""
    if state.initialized:
        state.session_id = str(uuid.uuid4())[:8]
        logger.info(f"New session: {state.session_id}")
    return []


# ==================== Settings 功能 ====================

def get_index_status() -> str:
    """获取索引状态"""
    if not state.initialized:
        return "未连接"
    
    try:
        status = state.bot.get_index_status(str(PROJECT_ROOT))
        return f"已索引: {status.get('indexed_files', 0)} 个文件"
    except Exception as e:
        return f"获取失败: {e}"


def sync_index(force: bool = False) -> str:
    """同步索引"""
    if not state.initialized:
        try:
            state.initialize()
        except Exception as e:
            return f"❌ 连接失败: {e}"
    
    try:
        result = state.bot.sync_index(force=force, workspace=str(PROJECT_ROOT))
        return f"✅ 索引完成: {result.get('indexed_files', 0)} 个文件"
    except Exception as e:
        return f"❌ 索引失败: {e}"


def clear_index() -> str:
    """清除索引"""
    if not state.initialized:
        return "未连接"
    
    try:
        state.bot.clear_index(str(PROJECT_ROOT))
        return "✅ 索引已清除"
    except Exception as e:
        return f"❌ 清除失败: {e}"


def list_skills() -> List[List[str]]:
    """列出技能"""
    if not state.initialized:
        try:
            state.initialize()
        except:
            return []
    
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
        return "未连接"
    
    if not skill_id.strip():
        return "❌ 请输入技能 ID"
    
    try:
        state.bot.toggle_skill(skill_id.strip(), enable)
        return f"✅ 技能 {skill_id} 已{'启用' if enable else '禁用'}"
    except Exception as e:
        return f"❌ 操作失败: {e}"


def get_rules() -> Dict[str, List[str]]:
    """获取规则"""
    if not state.initialized:
        try:
            state.initialize()
        except:
            return {"user_rules": [], "project_rules": []}
    
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
        try:
            state.initialize()
        except Exception as e:
            return f"❌ 连接失败: {e}"
    
    try:
        state.bot.add_rule(content.strip(), rule_type)
        return f"✅ 规则已添加"
    except Exception as e:
        return f"❌ 添加失败: {e}"


def list_mcp_servers() -> List[List[str]]:
    """列出 MCP 服务器"""
    if not state.initialized:
        try:
            state.initialize()
        except:
            return []
    
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
        try:
            state.initialize()
        except Exception as e:
            return f"❌ 连接失败: {e}"
    
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


def search_documents(query: str) -> str:
    """搜索文档"""
    if not query.strip():
        return "❌ 请输入搜索内容"
    
    if not state.initialized:
        try:
            state.initialize()
        except Exception as e:
            return f"❌ 连接失败: {e}"
    
    try:
        results = state.bot.search_documents(query.strip(), top_k=5)
        if not results.get('results'):
            return "未找到相关文档"
        
        output = "📚 搜索结果:\n\n"
        for i, r in enumerate(results['results'], 1):
            score = r.get('score', 0)
            source = r.get('source', 'unknown')
            content = r.get('content', '')[:200]
            output += f"**{i}. {source}** (相关度: {score:.2f})\n{content}...\n\n"
        
        return output
    except Exception as e:
        return f"❌ 搜索失败: {e}"


# ==================== 创建 UI ====================

def create_ui() -> gr.Blocks:
    """创建 Gradio UI"""
    
    with gr.Blocks(
        title="Agentic ChatBot",
        theme=gr.themes.Soft(),
    ) as app:
        
        gr.Markdown("""
        # 🤖 Agentic ChatBot
        
        **智能助手** - 支持 RAG、工具调用、技能、记忆等功能
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
                        placeholder="输入消息... (按 Enter 发送)",
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
            
            # ==================== Documents Tab ====================
            with gr.Tab("📚 Documents"):
                gr.Markdown("### 知识库搜索")
                
                with gr.Row():
                    search_input = gr.Textbox(
                        label="搜索内容",
                        placeholder="输入关键词搜索知识库...",
                        scale=4,
                    )
                    search_btn = gr.Button("🔍 搜索", scale=1)
                
                search_result = gr.Markdown(label="搜索结果")
                
                search_btn.click(search_documents, inputs=search_input, outputs=search_result)
                search_input.submit(search_documents, inputs=search_input, outputs=search_result)
            
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
        gr.Markdown(f"""
        ---
        **Agentic ChatBot SDK** v0.3.0 | 后端: `{state.backend_url}`
        
        *需要先启动后端服务: `cd backend && python run.py`*
        """)
    
    return app


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agentic ChatBot Gradio UI")
    parser.add_argument(
        "--backend-url",
        type=str,
        default=DEFAULT_BACKEND_URL,
        help=f"后端服务地址（默认: {DEFAULT_BACKEND_URL}）"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7870,
        help="Gradio 服务端口（默认: 7870）"
    )
    
    args = parser.parse_args()
    
    # 设置后端地址
    state.backend_url = args.backend_url
    
    print(f"""
╔═══════════════════════════════════════════════════╗
║           🤖 Agentic ChatBot Web UI               ║
╠═══════════════════════════════════════════════════╣
║  后端服务: {args.backend_url:<36}║
║  UI 端口: {args.port:<37}║
╠═══════════════════════════════════════════════════╣
║  ⚠️  请确保后端服务已启动！                       ║
║     cd backend && python run.py                   ║
╚═══════════════════════════════════════════════════╝
    """)
    
    app = create_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=args.port,
        share=False,
    )


if __name__ == "__main__":
    main()

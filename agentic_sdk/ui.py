# -*- coding: utf-8 -*-
"""
Gradio UI 组件（可选）

提供开箱即用的 Web UI，适用于：
- 演示和测试
- 客户无自定义 UI 时使用
- 快速原型开发

启动方式::

    # 方式 1: 命令行
    python -m agentic_sdk.ui --host 0.0.0.0 --port 7860
    
    # 方式 2: 代码
    from agentic_sdk.ui import launch_ui
    launch_ui(host="0.0.0.0", port=7860)
"""
from typing import Optional, List, Tuple
import uuid

try:
    import gradio as gr
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False
    gr = None

from .chatbot import ChatBot
from .config import ChatConfig


def create_ui(
    bot: Optional[ChatBot] = None,
    config: Optional[ChatConfig] = None,
    title: str = "Agentic ChatBot",
    description: str = "通用 AI 助手",
) -> "gr.Blocks":
    """
    创建 Gradio UI
    
    Args:
        bot: ChatBot 实例（可选，自动创建）
        config: 配置（当 bot 为 None 时使用）
        title: 页面标题
        description: 页面描述
    
    Returns:
        Gradio Blocks 应用
    """
    if not GRADIO_AVAILABLE:
        raise ImportError("Gradio is required for UI. Install with: pip install gradio")
    
    # 创建 ChatBot
    if bot is None:
        bot = ChatBot(config or ChatConfig())
    
    # 会话管理
    sessions = {}
    
    def get_session_id():
        return str(uuid.uuid4())[:8]
    
    def chat(message: str, history: List, session_id: str, debug_log: str):
        """处理对话"""
        if not message.strip():
            return history, "", debug_log
        
        # 添加用户消息
        history.append({"role": "user", "content": message})
        
        # Debug 日志
        debug_lines = [f"\n{'='*50}", f"📨 用户消息: {message}", f"🔑 Session: {session_id}", ""]
        
        # 获取响应
        try:
            response_text = ""
            for chunk in bot.chat_stream(message, session_id):
                # 记录所有 chunk 类型到 debug
                if chunk.type == "thinking":
                    debug_lines.append(f"🤔 {chunk.content}")
                elif chunk.type == "tool_call":
                    debug_lines.append(f"🔧 工具调用: {chunk.content}")
                    if chunk.metadata:
                        debug_lines.append(f"   参数: {chunk.metadata}")
                elif chunk.type == "tool_result":
                    debug_lines.append(f"📋 工具结果: {str(chunk.content)[:200]}")
                elif chunk.type == "text":
                    response_text += chunk.content or ""
                elif chunk.type == "error":
                    debug_lines.append(f"❌ 错误: {chunk.content}")
                elif chunk.type == "complete":
                    if chunk.metadata:
                        debug_lines.append(f"✅ 完成: 耗时 {chunk.metadata.get('duration_ms', '?')}ms")
                        debug_lines.append(f"   意图: {chunk.metadata.get('intent', {}).get('task_type', '?')}")
                        debug_lines.append(f"   工具: {chunk.metadata.get('used_tools', [])}")
            
            # 添加助手响应
            history.append({"role": "assistant", "content": response_text or "（无响应）"})
            debug_lines.append(f"\n💬 响应长度: {len(response_text)} 字符")
            
        except Exception as e:
            import traceback
            history.append({"role": "assistant", "content": f"错误: {str(e)}"})
            debug_lines.append(f"❌ 异常: {str(e)}")
            debug_lines.append(traceback.format_exc())
        
        # 更新 debug 日志（保留最近的）
        new_debug = debug_log + "\n".join(debug_lines)
        # 限制长度
        if len(new_debug) > 10000:
            new_debug = new_debug[-10000:]
        
        return history, "", new_debug
    
    def clear_chat(session_id: str):
        """清除对话"""
        bot.clear_conversation(session_id)
        return [], get_session_id()
    
    def get_tools_info():
        """获取工具信息"""
        tools = bot.list_tools()
        if not tools:
            return "暂无可用工具"
        
        lines = ["## 可用工具\n"]
        for tool in tools:
            lines.append(f"- **{tool['name']}**: {tool['description'][:100]}")
        return "\n".join(lines)
    
    def get_skills_info():
        """获取技能信息"""
        skills = bot.list_skills()
        if not skills:
            return "暂无可用技能"
        
        lines = ["## 可用技能\n"]
        for skill in skills:
            triggers = ", ".join(skill.get("triggers", [])[:3])
            lines.append(f"- **{skill['name']}**: {skill['description'][:80]}")
            if triggers:
                lines.append(f"  - 触发词: {triggers}")
        return "\n".join(lines)
    
    def clear_debug():
        """清除 Debug 日志"""
        return ""
    
    # 构建 UI
    with gr.Blocks(
        title=title,
        theme=gr.themes.Soft(),
        css="""
        .chatbot {min-height: 400px;}
        .info-panel {font-size: 14px;}
        .debug-log {font-family: monospace; font-size: 12px; background: #1e1e1e; color: #d4d4d4; padding: 10px; border-radius: 5px;}
        """
    ) as app:
        
        gr.Markdown(f"# 🤖 {title}")
        gr.Markdown(description)
        
        with gr.Row():
            # 左侧：对话区
            with gr.Column(scale=3):
                session_id = gr.State(get_session_id)
                
                chatbot = gr.Chatbot(
                    label="对话",
                    height=400,
                    elem_classes=["chatbot"],
                )
                
                with gr.Row():
                    message = gr.Textbox(
                        label="输入消息",
                        placeholder="输入你的问题...",
                        scale=4,
                        lines=2,
                    )
                    send_btn = gr.Button("发送", variant="primary", scale=1)
                
                with gr.Row():
                    clear_btn = gr.Button("🗑️ 清除对话")
                
                # Debug 面板
                with gr.Accordion("🐛 Debug 日志", open=False):
                    debug_log = gr.Textbox(
                        label="",
                        value="",
                        lines=15,
                        max_lines=20,
                        interactive=False,
                        elem_classes=["debug-log"],
                    )
                    clear_debug_btn = gr.Button("🧹 清除日志", size="sm")
            
            # 右侧：信息面板
            with gr.Column(scale=1):
                with gr.Accordion("🔧 工具", open=True):
                    tools_info = gr.Markdown(
                        get_tools_info,
                        elem_classes=["info-panel"],
                    )
                
                with gr.Accordion("📋 技能", open=False):
                    skills_info = gr.Markdown(
                        get_skills_info,
                        elem_classes=["info-panel"],
                    )
                
                with gr.Accordion("ℹ️ 关于", open=False):
                    gr.Markdown(f"""
                    **Agentic ChatBot SDK** v0.1.0
                    
                    一个通用可嵌入的 AI 助手 SDK。
                    
                    特性:
                    - ✅ RAG 知识库增强
                    - ✅ 记忆管理
                    - ✅ 自定义工具
                    - ✅ Skills 技能
                    - ✅ MCP 协议扩展
                    """)
        
        # 事件绑定
        send_btn.click(
            chat,
            inputs=[message, chatbot, session_id, debug_log],
            outputs=[chatbot, message, debug_log],
        )
        
        message.submit(
            chat,
            inputs=[message, chatbot, session_id, debug_log],
            outputs=[chatbot, message, debug_log],
        )
        
        clear_btn.click(
            clear_chat,
            inputs=[session_id],
            outputs=[chatbot, session_id],
        )
        
        clear_debug_btn.click(
            clear_debug,
            inputs=[],
            outputs=[debug_log],
        )
    
    return app


def launch_ui(
    bot: Optional[ChatBot] = None,
    config: Optional[ChatConfig] = None,
    host: str = "0.0.0.0",
    port: int = 7860,
    share: bool = False,
    **kwargs,
):
    """
    启动 Gradio UI
    
    Args:
        bot: ChatBot 实例
        config: 配置
        host: 绑定主机
        port: 绑定端口
        share: 是否创建公共链接
        **kwargs: 传递给 gr.Blocks.launch() 的其他参数
    """
    app = create_ui(bot, config)
    app.launch(
        server_name=host,
        server_port=port,
        share=share,
        **kwargs,
    )


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agentic ChatBot Gradio UI")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=7860, help="Port to bind")
    parser.add_argument("--share", action="store_true", help="Create public link")
    parser.add_argument("--config", help="Config file path")
    
    args = parser.parse_args()
    
    config = None
    if args.config:
        config = ChatConfig.from_file(args.config)
    
    launch_ui(
        config=config,
        host=args.host,
        port=args.port,
        share=args.share,
    )


if __name__ == "__main__":
    main()


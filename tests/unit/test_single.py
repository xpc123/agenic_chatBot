#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单个测试工具 - 用于快速调试特定场景

用法:
    # 交互模式
    python tests/test_single.py
    
    # 直接测试
    python tests/test_single.py "帮我看看 /tmp 目录"
    
    # 测试多轮对话
    python tests/test_single.py --multi "你好" "我的名字是张三" "我叫什么？"
"""
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentic_sdk import ChatBot


def test_message(bot: ChatBot, message: str, session_id: str = "debug", verbose: bool = True):
    """测试单条消息"""
    print(f"\n{'='*60}")
    print(f"📨 消息: {message}")
    print(f"🔑 Session: {session_id}")
    print("-" * 60)
    
    response_parts = []
    
    for chunk in bot.chat_stream(message, session_id):
        if chunk.type == "thinking":
            if verbose:
                print(f"🤔 {chunk.content}")
        elif chunk.type == "tool_call":
            print(f"🔧 工具: {chunk.content}")
            if verbose and chunk.metadata:
                print(f"   参数: {chunk.metadata}")
        elif chunk.type == "tool_result":
            result_preview = str(chunk.content)[:300]
            print(f"📋 结果: {result_preview}...")
        elif chunk.type == "text":
            response_parts.append(chunk.content or "")
        elif chunk.type == "error":
            print(f"❌ 错误: {chunk.content}")
        elif chunk.type == "complete":
            if verbose and chunk.metadata:
                print(f"\n⏱️ 耗时: {chunk.metadata.get('duration_ms', '?')}ms")
                print(f"🎯 意图: {chunk.metadata.get('intent', {}).get('task_type', '?')}")
                print(f"🔧 工具: {chunk.metadata.get('used_tools', [])}")
    
    response = "".join(response_parts)
    print(f"\n💬 响应:")
    print("-" * 40)
    print(response)
    print("-" * 40)
    print(f"📏 长度: {len(response)} 字符")
    
    return response


def interactive_mode(bot: ChatBot):
    """交互模式"""
    print("\n🤖 Agentic ChatBot 交互测试")
    print("输入 'quit' 退出, 'clear' 清除会话")
    print("=" * 60)
    
    session_id = "interactive-debug"
    
    while True:
        try:
            message = input("\n你: ").strip()
            
            if not message:
                continue
            if message.lower() == "quit":
                print("👋 再见!")
                break
            if message.lower() == "clear":
                bot.clear_conversation(session_id)
                print("🗑️ 会话已清除")
                continue
                
            test_message(bot, message, session_id)
            
        except KeyboardInterrupt:
            print("\n👋 再见!")
            break
        except Exception as e:
            print(f"❌ 错误: {e}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="单个测试工具")
    parser.add_argument("messages", nargs="*", help="要测试的消息")
    parser.add_argument("--multi", "-m", action="store_true", help="多轮对话模式")
    parser.add_argument("--session", "-s", default="debug", help="Session ID")
    parser.add_argument("--quiet", "-q", action="store_true", help="简洁输出")
    
    args = parser.parse_args()
    
    print("🚀 初始化 ChatBot...")
    bot = ChatBot()
    print("✅ 初始化完成")
    
    if not args.messages:
        # 交互模式
        interactive_mode(bot)
    elif args.multi or len(args.messages) > 1:
        # 多轮对话
        session_id = args.session
        for msg in args.messages:
            test_message(bot, msg, session_id, verbose=not args.quiet)
    else:
        # 单条消息
        test_message(bot, args.messages[0], args.session, verbose=not args.quiet)


if __name__ == "__main__":
    main()


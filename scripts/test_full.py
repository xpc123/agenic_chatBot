# -*- coding: utf-8 -*-
"""
完整功能测试 - 验证 UI 和 SDK 一致性
"""
import sys
import asyncio
from pathlib import Path

# 设置路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'backend'))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / 'backend' / '.env')


def test_chat():
    """测试对话功能"""
    print("\n" + "=" * 60)
    print("🧪 测试 1: 对话功能（记忆保持）")
    print("=" * 60)
    
    from agentic_sdk import ChatBot, ChatConfig
    
    config = ChatConfig(
        enable_rag=True,
        enable_memory=True,
        enable_skills=True,
    )
    
    bot = ChatBot(config)
    
    # 第一个问题
    print("\n📋 问题 1: 查看当前目录")
    print("-" * 40)
    
    response1 = bot.chat("查看当前目录下有哪些文件和目录")
    print(f"回答 (前 300 字符):\n{response1.text[:300]}...")
    print(f"工具调用: {len(response1.tool_calls)} 次")
    
    # 第二个问题（应使用记忆）
    print("\n📋 问题 2: 后端架构（基于记忆）")
    print("-" * 40)
    
    response2 = bot.chat("介绍一下后端项目架构", session_id=response1.session_id)
    print(f"回答 (前 500 字符):\n{response2.text[:500]}...")
    print(f"工具调用: {len(response2.tool_calls)} 次")
    
    # 评估
    success = "抱歉" not in response2.text
    print(f"\n结果: {'✅ 成功' if success else '❌ 失败'}")
    
    return success


def test_settings():
    """测试设置功能"""
    print("\n" + "=" * 60)
    print("🧪 测试 2: 设置功能（UI ↔ SDK 一致性）")
    print("=" * 60)
    
    from agentic_sdk import SettingsManager
    
    settings = SettingsManager(workspace=str(PROJECT_ROOT))
    
    # 检查各项功能
    checks = {
        "索引": len(settings.get_indexed_files()) > 0,
        "规则": settings.add_user_rule("test_rule"),
        "技能": len(settings.list_skills()) > 0,
        "MCP": settings.add_mcp_server("test", "http"),
    }
    
    print("\n功能检查:")
    all_pass = True
    for name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"  {status} {name}: {'通过' if result else '失败'}")
        if not result:
            all_pass = False
    
    # 清理测试数据
    settings.remove_user_rule("test_rule")
    settings.remove_mcp_server("test")
    
    return all_pass


def test_stream():
    """测试流式输出"""
    print("\n" + "=" * 60)
    print("🧪 测试 3: 流式输出")
    print("=" * 60)
    
    from agentic_sdk import ChatBot
    
    bot = ChatBot()
    
    print("\n📋 问题: 简单问候")
    print("-" * 40)
    
    text = ""
    chunks = 0
    for chunk in bot.chat_stream("你好，请用一句话介绍自己"):
        if chunk.is_text and chunk.content:
            text += chunk.content
            chunks += 1
    
    print(f"回答: {text}")
    print(f"块数: {chunks}")
    
    success = len(text) > 0 and chunks > 0
    print(f"\n结果: {'✅ 成功' if success else '❌ 失败'}")
    
    return success


def main():
    """主测试入口"""
    print("=" * 60)
    print("🔥 Agentic ChatBot 完整功能测试")
    print("=" * 60)
    
    results = {}
    
    try:
        results["对话功能"] = test_chat()
    except Exception as e:
        print(f"❌ 对话测试失败: {e}")
        results["对话功能"] = False
    
    try:
        results["设置功能"] = test_settings()
    except Exception as e:
        print(f"❌ 设置测试失败: {e}")
        results["设置功能"] = False
    
    try:
        results["流式输出"] = test_stream()
    except Exception as e:
        print(f"❌ 流式测试失败: {e}")
        results["流式输出"] = False
    
    # 汇总
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    all_pass = True
    for name, result in results.items():
        status = "✅" if result else "❌"
        print(f"  {status} {name}")
        if not result:
            all_pass = False
    
    print("\n" + "=" * 60)
    if all_pass:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 部分测试失败")
    print("=" * 60)
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())


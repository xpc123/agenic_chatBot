# -*- coding: utf-8 -*-
"""
测试记忆功能 - 验证工具结果是否被正确保存和使用
"""
import sys
import asyncio
from pathlib import Path

# 设置路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'backend'))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / 'backend' / '.env')

from app.core.cursor_style_orchestrator import CursorStyleOrchestrator
from app.core.practical_tools import get_practical_tools
from app.llm import get_llm_client


async def test_memory():
    """测试记忆功能"""
    print("=" * 60)
    print("🧪 测试记忆功能")
    print("=" * 60)
    
    # 初始化
    llm = get_llm_client()
    tools = get_practical_tools()
    
    orchestrator = CursorStyleOrchestrator(
        llm_client=llm,
        tools=tools,
        enable_rag=True,
        enable_skills=True,
        enable_memory=True,
        workspace_path=str(PROJECT_ROOT),
    )
    
    session_id = "test_memory_session"
    user_id = "test_user"
    
    # 清除旧会话
    orchestrator.clear_session(session_id)
    
    print("\n📋 测试 1: 第一个问题 - 列出目录")
    print("-" * 40)
    
    response1 = ""
    async for chunk in orchestrator.chat_stream(
        message="查看当前目录下有哪些文件和目录",
        session_id=session_id,
        user_id=user_id,
    ):
        if chunk.type == "text":
            response1 += chunk.content or ""
        elif chunk.type == "tool_call":
            print(f"  🔧 调用工具: {chunk.metadata.get('tool', 'unknown')}")
        elif chunk.type == "tool_result":
            print(f"  ✅ 工具结果: {chunk.content}")
    
    print(f"\n📝 回答 1 (前 200 字符):\n{response1[:200]}...")
    
    # 检查会话状态
    print("\n📊 检查会话状态:")
    if session_id in orchestrator.sessions:
        session = orchestrator.sessions[session_id]
        history = session.get("history", [])
        tool_results = session.get("tool_results", [])
        print(f"  - 对话历史: {len(history)} 条")
        print(f"  - 工具结果: {len(tool_results)} 条")
        
        for tr in tool_results:
            print(f"    - {tr.get('tool')}: {len(tr.get('result', ''))} chars")
    else:
        print("  ❌ 会话不存在!")
    
    # 检查上下文摘要
    print("\n📄 上下文摘要:")
    context_summary = orchestrator.get_session_context_summary(session_id)
    print(f"  长度: {len(context_summary)} chars")
    if context_summary:
        print(f"  内容 (前 500 字符):\n{context_summary[:500]}...")
    else:
        print("  ❌ 无上下文摘要!")
    
    print("\n" + "=" * 60)
    print("📋 测试 2: 第二个问题 - 后端架构（应使用记忆）")
    print("-" * 40)
    
    response2 = ""
    tool_calls_count = 0
    async for chunk in orchestrator.chat_stream(
        message="介绍一下后端项目架构",
        session_id=session_id,
        user_id=user_id,
    ):
        if chunk.type == "text":
            response2 += chunk.content or ""
        elif chunk.type == "tool_call":
            tool_calls_count += 1
            print(f"  🔧 调用工具 #{tool_calls_count}: {chunk.metadata.get('tool', 'unknown')}")
        elif chunk.type == "tool_result":
            print(f"  ✅ 工具结果: {chunk.content}")
        elif chunk.type == "error":
            print(f"  ❌ 错误: {chunk.content}")
    
    print(f"\n📝 回答 2:\n{response2[:500]}...")
    
    # 评估结果
    print("\n" + "=" * 60)
    print("📊 测试结果:")
    print("-" * 40)
    
    if "抱歉" in response2 or "复杂" in response2:
        print("❌ 失败: AI 未能回答问题")
        print("   原因: 可能是 max_iterations 达到上限")
    elif tool_calls_count == 0:
        print("✅ 成功: AI 直接使用记忆回答，没有调用工具")
    elif tool_calls_count <= 2:
        print("⚠️ 部分成功: AI 只调用了少量工具")
    else:
        print(f"❌ 失败: AI 调用了 {tool_calls_count} 次工具（应该使用记忆）")
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_memory())


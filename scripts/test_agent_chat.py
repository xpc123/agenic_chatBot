# -*- coding: utf-8 -*-
"""测试 agent.chat 功能"""
import asyncio
import sys
from pathlib import Path

# 设置路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'backend'))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / 'backend' / '.env')

from app.core import AgentEngine, MemoryManager, ToolExecutor
from app.core.context_loader import ContextLoader
from app.mcp import mcp_registry


async def test_chat():
    """测试 agent.chat"""
    print("=" * 60)
    print("初始化 Agent...")
    
    memory = MemoryManager()
    tool_executor = ToolExecutor(mcp_registry)
    context_loader = ContextLoader()
    
    agent = AgentEngine(
        memory_manager=memory,
        tool_executor=tool_executor,
        context_loader=context_loader,
        enable_summarization=False,
    )
    
    print("✅ Agent 初始化完成")
    print("=" * 60)
    
    # 测试 1: 计算
    print("\n📝 测试 1: 计算 1+2+3+4+5")
    print("-" * 40)
    async for chunk in agent.chat(message="计算 1+2+3+4+5", session_id="test-v2"):
        chunk_type = chunk.get("type", "")
        content = chunk.get("content", "")
        print(f"  [{chunk_type}] {content[:100]}...")
    
    # 测试 2: 时间
    print("\n📝 测试 2: 现在几点了")
    print("-" * 40)
    async for chunk in agent.chat(message="现在几点了？", session_id="test-v2"):
        chunk_type = chunk.get("type", "")
        content = chunk.get("content", "")
        print(f"  [{chunk_type}] {content[:100]}...")
    
    # 测试 3: 简单问题
    print("\n📝 测试 3: 简单问题")
    print("-" * 40)
    async for chunk in agent.chat(message="你好，介绍一下你自己", session_id="test-v2"):
        chunk_type = chunk.get("type", "")
        content = chunk.get("content", "")
        print(f"  [{chunk_type}] {content[:100]}...")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")


if __name__ == "__main__":
    asyncio.run(test_chat())

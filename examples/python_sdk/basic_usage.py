#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Python SDK 基础用法示例
"""
import sys
sys.path.insert(0, "../..")

from agentic_sdk import ChatBot, ChatConfig


def example_basic():
    """基础对话"""
    print("=" * 50)
    print("示例 1: 基础对话")
    print("=" * 50)
    
    bot = ChatBot()
    
    response = bot.chat("你好，请介绍一下你自己")
    print(f"响应: {response.text}")
    print(f"延迟: {response.latency_ms}ms")


def example_stream():
    """流式对话"""
    print("\n" + "=" * 50)
    print("示例 2: 流式对话")
    print("=" * 50)
    
    bot = ChatBot()
    
    print("响应: ", end="")
    for chunk in bot.chat_stream("讲一个简短的笑话"):
        if chunk.is_text:
            print(chunk.content, end="", flush=True)
    print()


def example_custom_tool():
    """自定义工具"""
    print("\n" + "=" * 50)
    print("示例 3: 自定义工具")
    print("=" * 50)
    
    bot = ChatBot()
    
    @bot.tool
    def get_weather(city: str) -> str:
        """获取城市天气"""
        # 模拟天气 API
        weather_data = {
            "北京": "晴，25°C",
            "上海": "多云，28°C",
            "深圳": "阵雨，30°C",
        }
        return weather_data.get(city, f"{city}：天气数据不可用")
    
    response = bot.chat("北京今天天气怎么样？")
    print(f"响应: {response.text}")
    
    if response.tool_calls:
        print(f"调用的工具: {[tc.name for tc in response.tool_calls]}")


def example_session():
    """会话管理"""
    print("\n" + "=" * 50)
    print("示例 4: 会话管理")
    print("=" * 50)
    
    bot = ChatBot()
    
    # 第一轮对话
    r1 = bot.chat("我叫小明", session_id="user123")
    print(f"第一轮: {r1.text}")
    
    # 第二轮对话（记住上下文）
    r2 = bot.chat("你还记得我叫什么吗？", session_id="user123")
    print(f"第二轮: {r2.text}")


def example_config():
    """自定义配置"""
    print("\n" + "=" * 50)
    print("示例 5: 自定义配置")
    print("=" * 50)
    
    # 最小配置（仅对话，无 RAG/Memory/Skills）
    config = ChatConfig.minimal()
    bot = ChatBot(config)
    
    response = bot.chat("你好")
    print(f"响应: {response.text}")
    
    # 完整配置
    full_config = ChatConfig.full()
    full_bot = ChatBot(full_config)
    
    print("完整配置已启用: RAG, Memory, Skills, MCP")


async def example_async():
    """异步用法"""
    print("\n" + "=" * 50)
    print("示例 6: 异步用法")
    print("=" * 50)
    
    bot = ChatBot()
    
    response = await bot.chat_async("你好")
    print(f"响应: {response.text}")
    
    # 异步流式
    print("流式响应: ", end="")
    async for chunk in bot.chat_stream_async("讲个短故事"):
        if chunk.is_text:
            print(chunk.content, end="", flush=True)
    print()


if __name__ == "__main__":
    # 运行同步示例
    example_basic()
    example_stream()
    example_custom_tool()
    example_session()
    example_config()
    
    # 运行异步示例
    import asyncio
    asyncio.run(example_async())
    
    print("\n✅ 所有示例运行完成！")


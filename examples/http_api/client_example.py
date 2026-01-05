#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HTTP API 客户端示例

演示如何通过 HTTP 调用 Agentic ChatBot API。
适用于任何语言（Python, JavaScript, Java, C++, Go 等）。
"""
import requests
import json
import sseclient  # pip install sseclient-py


# API 服务器地址
API_BASE = "http://localhost:8000"


def example_sync_chat():
    """同步对话"""
    print("=" * 50)
    print("示例 1: 同步对话")
    print("=" * 50)
    
    response = requests.post(
        f"{API_BASE}/api/chat",
        json={
            "message": "你好，请介绍一下你自己",
            "session_id": "demo123",
        },
        headers={"Content-Type": "application/json"},
    )
    
    if response.ok:
        data = response.json()
        print(f"响应: {data['text']}")
        print(f"会话 ID: {data['session_id']}")
        print(f"延迟: {data['latency_ms']}ms")
    else:
        print(f"错误: {response.status_code} - {response.text}")


def example_stream_chat():
    """流式对话 (SSE)"""
    print("\n" + "=" * 50)
    print("示例 2: 流式对话 (SSE)")
    print("=" * 50)
    
    response = requests.post(
        f"{API_BASE}/api/chat/stream",
        json={
            "message": "讲一个简短的笑话",
            "session_id": "demo123",
        },
        headers={"Content-Type": "application/json"},
        stream=True,
    )
    
    if response.ok:
        print("响应: ", end="")
        
        client = sseclient.SSEClient(response)
        for event in client.events():
            try:
                data = json.loads(event.data)
                
                if data["type"] == "text":
                    print(data["content"], end="", flush=True)
                elif data["type"] == "tool_call":
                    print(f"\n[调用工具: {data.get('tool_name')}]", end="")
                elif data["type"] == "complete":
                    print("\n[完成]")
                    break
                    
            except json.JSONDecodeError:
                pass
    else:
        print(f"错误: {response.status_code}")


def example_list_tools():
    """获取工具列表"""
    print("\n" + "=" * 50)
    print("示例 3: 获取工具列表")
    print("=" * 50)
    
    response = requests.get(f"{API_BASE}/api/tools")
    
    if response.ok:
        tools = response.json()
        print(f"可用工具 ({len(tools)} 个):")
        for tool in tools[:5]:  # 只显示前 5 个
            print(f"  - {tool['name']}: {tool['description'][:50]}...")
    else:
        print(f"错误: {response.status_code}")


def example_list_skills():
    """获取技能列表"""
    print("\n" + "=" * 50)
    print("示例 4: 获取技能列表")
    print("=" * 50)
    
    response = requests.get(f"{API_BASE}/api/skills")
    
    if response.ok:
        skills = response.json()
        print(f"可用技能 ({len(skills)} 个):")
        for skill in skills:
            print(f"  - {skill['name']}: {skill['description'][:50]}...")
    else:
        print(f"错误: {response.status_code}")


def example_session_management():
    """会话管理"""
    print("\n" + "=" * 50)
    print("示例 5: 会话管理")
    print("=" * 50)
    
    # 列出会话
    response = requests.get(f"{API_BASE}/api/sessions")
    if response.ok:
        sessions = response.json()["sessions"]
        print(f"当前会话: {sessions}")
    
    # 清除会话
    response = requests.delete(f"{API_BASE}/api/sessions/demo123")
    if response.ok:
        print("会话 demo123 已清除")


def example_health_check():
    """健康检查"""
    print("\n" + "=" * 50)
    print("示例 6: 健康检查")
    print("=" * 50)
    
    response = requests.get(f"{API_BASE}/health")
    
    if response.ok:
        data = response.json()
        print(f"状态: {data['status']}")
        print(f"版本: {data['version']}")
        print(f"时间: {data['timestamp']}")
    else:
        print(f"服务不可用: {response.status_code}")


# ==================== 其他语言示例 ====================

CURL_EXAMPLE = """
# cURL 示例

# 同步对话
curl -X POST http://localhost:8000/api/chat \\
  -H "Content-Type: application/json" \\
  -d '{"message": "你好", "session_id": "test"}'

# 流式对话
curl -X POST http://localhost:8000/api/chat/stream \\
  -H "Content-Type: application/json" \\
  -d '{"message": "讲个故事", "session_id": "test"}'

# 获取工具
curl http://localhost:8000/api/tools
"""

JAVASCRIPT_EXAMPLE = """
// JavaScript/Node.js 示例

// 同步对话
const response = await fetch('http://localhost:8000/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: '你好', session_id: 'test' })
});
const data = await response.json();
console.log(data.text);

// 流式对话 (SSE)
const eventSource = new EventSource('http://localhost:8000/api/chat/stream', {
  method: 'POST',
  body: JSON.stringify({ message: '讲个故事' })
});
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'text') {
    process.stdout.write(data.content);
  }
};
"""

CPP_EXAMPLE = """
// C++ 示例 (使用 libcurl)

#include <curl/curl.h>
#include <string>

std::string chat(const std::string& message) {
    CURL* curl = curl_easy_init();
    
    std::string url = "http://localhost:8000/api/chat";
    std::string body = R"({"message": ")" + message + R"(", "session_id": "cpp"})";
    
    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, body.c_str());
    
    // ... 处理响应
    
    curl_easy_cleanup(curl);
    return response;
}
"""


if __name__ == "__main__":
    print("Agentic ChatBot HTTP API 客户端示例")
    print("请确保 API 服务器已启动: python -m agentic_sdk.server")
    print()
    
    try:
        example_health_check()
        example_sync_chat()
        example_stream_chat()
        example_list_tools()
        example_list_skills()
        example_session_management()
        
        print("\n" + "=" * 50)
        print("其他语言示例:")
        print("=" * 50)
        print(CURL_EXAMPLE)
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到 API 服务器")
        print("请先启动服务器: python -m agentic_sdk.server")


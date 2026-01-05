#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Virtuoso SKILL 集成示例

演示如何将 Agentic ChatBot 集成到 Cadence Virtuoso 环境。

架构::

    ┌─────────────────────┐      HTTP       ┌─────────────────────┐
    │    Virtuoso         │ ◄────────────►  │  Agentic ChatBot    │
    │    (SKILL)          │                 │  (Python Server)    │
    │                     │  /api/chat      │                     │
    │  - 调用 API         │                 │  - AI 对话          │
    │  - 执行 SKILL       │ ◄──────────────  │  - 调用 MCP         │
    └─────────────────────┘    SKILL 命令   └─────────────────────┘
"""
import sys
sys.path.insert(0, "../..")

from agentic_sdk import ChatBot, ChatConfig


def create_virtuoso_chatbot():
    """
    创建集成 Virtuoso MCP 的 ChatBot
    """
    config = ChatConfig(
        enable_rag=True,
        enable_skills=True,
        enable_memory=True,
    )
    
    # 配置 MCP 服务器（连接 Virtuoso MCP）
    config.mcp.servers = [
        {
            "name": "virtuoso-mcp",
            "url": "http://shbjlnxade1:8080",
            "description": "Cadence Virtuoso MCP Server",
        }
    ]
    
    bot = ChatBot(config)
    
    # 添加 Virtuoso 特定的工具
    @bot.tool
    def execute_skill(code: str) -> str:
        """
        在 Virtuoso 中执行 SKILL 代码
        
        Args:
            code: SKILL 代码
        
        Returns:
            执行结果
        """
        # 通过 MCP 调用 Virtuoso
        # 这里可以直接调用 virtuoso-mcp 的 skill_interpreter
        import requests
        
        try:
            response = requests.post(
                "http://shbjlnxade1:8080/tools/mcp_virtuoso_skill_interpreter",
                json={"code": code},
                timeout=30,
            )
            if response.ok:
                return response.json().get("result", "执行完成")
            else:
                return f"执行失败: {response.text}"
        except Exception as e:
            return f"连接 Virtuoso MCP 失败: {e}"
    
    @bot.tool
    def query_virtuoso_doc(query: str) -> str:
        """
        查询 Virtuoso 文档
        
        Args:
            query: 查询内容
        
        Returns:
            文档结果
        """
        import requests
        
        try:
            response = requests.post(
                "http://shbjlnxade1:8080/tools/mcp_virtuoso_doc",
                json={"query": query},
                timeout=30,
            )
            if response.ok:
                return response.json().get("result", "未找到相关文档")
            else:
                return f"查询失败: {response.text}"
        except Exception as e:
            return f"连接 Virtuoso MCP 失败: {e}"
    
    return bot


def example_skill_generation():
    """SKILL 代码生成示例"""
    print("=" * 50)
    print("示例 1: SKILL 代码生成")
    print("=" * 50)
    
    bot = create_virtuoso_chatbot()
    
    response = bot.chat("帮我写一个 SKILL 函数，计算两个数的和")
    print(f"响应:\n{response.text}")


def example_skill_execution():
    """SKILL 代码执行示例"""
    print("\n" + "=" * 50)
    print("示例 2: SKILL 代码执行")
    print("=" * 50)
    
    bot = create_virtuoso_chatbot()
    
    response = bot.chat("在 Virtuoso 中执行 SKILL 代码: 1 + 2 * 3")
    print(f"响应:\n{response.text}")


def example_virtuoso_help():
    """Virtuoso 使用帮助"""
    print("\n" + "=" * 50)
    print("示例 3: Virtuoso 使用帮助")
    print("=" * 50)
    
    bot = create_virtuoso_chatbot()
    
    response = bot.chat("如何在 Virtuoso 中创建一个新的 cellview？")
    print(f"响应:\n{response.text}")


# ==================== SKILL 客户端代码 ====================

SKILL_CLIENT_CODE = '''
; SKILL 客户端代码 - 在 Virtuoso 中调用 Agentic ChatBot API
;
; 将此代码加载到 Virtuoso 中:
; load("agentic_chatbot.il")
;
; 使用方法:
; agenticChat("你好，帮我分析当前设计")

procedure(agenticChat(message @optional (sessionId "virtuoso"))
  let((url body response)
    
    ; API 地址
    url = "http://localhost:8000/api/chat"
    
    ; 构建请求
    body = sprintf(nil "{\"message\": \"%s\", \"session_id\": \"%s\"}" 
                   message sessionId)
    
    ; 发送 HTTP 请求 (需要 Virtuoso 的 HTTP 扩展)
    response = httpPost(url body)
    
    ; 解析响应
    if(response then
      printf("AI 助手: %s\n" parseJson(response)->text)
    else
      printf("错误: 无法连接到 AI 服务\n")
    )
  )
)

; 快捷命令
procedure(ai(message)
  agenticChat(message)
)

; 示例用法:
; ai("帮我检查当前 schematic 的 DRC 问题")
; ai("如何优化这个 layout 的面积？")
; ai("解释 nmos 的工作原理")

printf("Agentic ChatBot SKILL 客户端已加载\n")
printf("使用 ai(\"你的问题\") 与 AI 助手对话\n")
'''


def generate_skill_client():
    """生成 SKILL 客户端代码"""
    print("\n" + "=" * 50)
    print("SKILL 客户端代码")
    print("=" * 50)
    print(SKILL_CLIENT_CODE)
    
    # 保存到文件
    with open("agentic_chatbot.il", "w") as f:
        f.write(SKILL_CLIENT_CODE)
    
    print("\n已保存到 agentic_chatbot.il")
    print("在 Virtuoso 中加载: load(\"agentic_chatbot.il\")")


if __name__ == "__main__":
    print("Virtuoso SKILL 集成示例")
    print()
    
    # 运行示例
    example_skill_generation()
    example_skill_execution()
    example_virtuoso_help()
    
    # 生成 SKILL 客户端
    generate_skill_client()
    
    print("\n✅ Virtuoso 集成示例完成！")


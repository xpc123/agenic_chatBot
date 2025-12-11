"""
🚀 3 行代码集成示例 - 极简版

演示如何用最少的代码给你的应用加上 AI 助手
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sdk', 'python'))

from chatbot_sdk import ChatBot

# ============================================
# 示例 1: 最简单的用法（3 行代码）
# ============================================

def example_minimal():
    """最简集成 - 3 行代码"""
    print("=" * 60)
    print("示例 1: 最简集成（3 行代码）")
    print("=" * 60)
    
    # 这就是全部代码！
    bot = ChatBot(base_url="http://localhost:8000")
    response = bot.chat("你好，介绍一下你的功能")
    print(f"\n💬 {response}\n")


# ============================================
# 示例 2: @路径引用（Cursor 风格）
# ============================================

def example_path_reference():
    """Cursor 风格的文件引用"""
    print("=" * 60)
    print("示例 2: @路径引用（Cursor 风格）")
    print("=" * 60)
    
    bot = ChatBot(base_url="http://localhost:8000")
    
    # 引用文件进行分析
    response = bot.chat("@backend/app/main.py 这个文件的主要功能是什么？")
    print(f"\n💬 {response}\n")


# ============================================
# 示例 3: 流式输出
# ============================================

def example_streaming():
    """实时流式响应"""
    print("=" * 60)
    print("示例 3: 流式输出")
    print("=" * 60)
    
    bot = ChatBot(base_url="http://localhost:8000")
    
    print("\n💬 ", end="", flush=True)
    for chunk in bot.chat_stream("用一句话介绍 Python"):
        print(chunk, end="", flush=True)
    print("\n")


# ============================================
# 示例 4: Flask 集成（完整示例）
# ============================================

def example_flask_integration():
    """Flask 应用集成"""
    print("=" * 60)
    print("示例 4: Flask 应用集成代码")
    print("=" * 60)
    
    code = '''
from flask import Flask, request, jsonify
from chatbot_sdk import ChatBot

app = Flask(__name__)
bot = ChatBot(base_url="http://localhost:8000")

@app.route('/api/chat', methods=['POST'])
def chat():
    message = request.json.get('message')
    response = bot.chat(message)
    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(port=5000)
'''
    print(code)
    print("\n✓ 复制上面的代码到你的 Flask 应用即可！\n")


# ============================================
# 示例 5: RAG 知识库
# ============================================

def example_rag():
    """RAG 知识库集成"""
    print("=" * 60)
    print("示例 5: RAG 知识库")
    print("=" * 60)
    
    bot = ChatBot(base_url="http://localhost:8000")
    
    # 假设已经上传了文档到 RAG
    response = bot.chat(
        "我们的产品有哪些核心功能？", 
        use_rag=True
    )
    print(f"\n💬 {response}\n")


# ============================================
# 示例 6: 工具调用
# ============================================

def example_tools():
    """AI 自动调用工具"""
    print("=" * 60)
    print("示例 6: 工具调用")
    print("=" * 60)
    
    bot = ChatBot(base_url="http://localhost:8000")
    
    # AI 会自动判断是否需要使用工具
    response = bot.chat("现在几点了？")
    print(f"\n💬 {response}\n")
    
    response = bot.chat("帮我计算 123 * 456")
    print(f"\n💬 {response}\n")


# ============================================
# 实际业务场景示例
# ============================================

def example_customer_support():
    """客服助手场景"""
    print("=" * 60)
    print("实际场景: 客服助手")
    print("=" * 60)
    
    bot = ChatBot(base_url="http://localhost:8000")
    
    # 客户询问
    customer_question = "如何重置密码？"
    
    # AI 基于文档库回答
    response = bot.chat(
        customer_question,
        use_rag=True,
        context={
            "user_id": "12345",
            "product": "premium"
        }
    )
    
    print(f"\n👤 客户: {customer_question}")
    print(f"🤖 助手: {response}\n")


def example_code_assistant():
    """代码助手场景"""
    print("=" * 60)
    print("实际场景: 代码助手")
    print("=" * 60)
    
    bot = ChatBot(base_url="http://localhost:8000")
    
    # 开发者询问
    question = "@backend/app/api/chat.py 这个 API 的错误处理逻辑有什么问题？"
    
    response = bot.chat(question)
    
    print(f"\n👨‍💻 开发者: {question}")
    print(f"🤖 助手: {response}\n")


def example_data_analyst():
    """数据分析助手场景"""
    print("=" * 60)
    print("实际场景: 数据分析助手")
    print("=" * 60)
    
    bot = ChatBot(base_url="http://localhost:8000")
    
    # 分析师询问
    question = "查询最近 7 天的用户增长数据，并生成趋势报告"
    
    # AI 会自动调用数据库工具
    response = bot.chat(question)
    
    print(f"\n📊 分析师: {question}")
    print(f"🤖 助手: {response}\n")


# ============================================
# 运行所有示例
# ============================================

if __name__ == "__main__":
    print("\n🚀 Agentic ChatBot - 3 行代码集成示例\n")
    print("=" * 60)
    print("提示: 确保后端服务已启动 (python run.py)")
    print("=" * 60)
    
    try:
        # 基础示例
        example_minimal()
        example_path_reference()
        example_streaming()
        
        # 框架集成
        example_flask_integration()
        
        # 功能示例
        example_rag()
        example_tools()
        
        # 实际场景
        example_customer_support()
        example_code_assistant()
        example_data_analyst()
        
        print("\n" + "=" * 60)
        print("✅ 所有示例运行完成！")
        print("=" * 60)
        print("\n📖 查看更多: docs/QUICKSTART.md")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        print("\n💡 提示:")
        print("   1. 确保后端服务已启动: cd backend && python run.py")
        print("   2. 确保已配置 API Key: backend/.env")
        print("   3. 确保服务地址正确: http://localhost:8000")

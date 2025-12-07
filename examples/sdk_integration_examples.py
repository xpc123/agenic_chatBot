"""
SDK集成示例 - 方式一：代码集成

演示如何在你的产品中集成 Agentic ChatBot SDK
"""
import sys
import os

# 添加SDK路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sdk', 'python'))

from chatbot_sdk import ChatBotSDK, ChatBotConfig


# ==================== 示例1：基础集成 ====================

def example_basic_chat():
    """示例1：基础对话"""
    print("=" * 60)
    print("示例1：基础对话")
    print("=" * 60)
    
    # 配置
    config = ChatBotConfig(
        app_id="demo_app",
        app_secret="demo_secret_key",
        base_url="http://localhost:8000",
    )
    
    # 创建客户端
    client = ChatBotSDK(config)
    
    # 初始化
    print("\n[1] 初始化集成...")
    result = client.initialize()
    print(f"✓ 初始化成功: {result['message']}")
    
    # 发送消息
    print("\n[2] 发送消息...")
    response = client.chat(
        message="你好，请介绍一下自己的功能",
        stream=False
    )
    print(f"\n回复: {response}")


# ==================== 示例2：流式对话 ====================

def example_streaming_chat():
    """示例2：流式对话"""
    print("\n" + "=" * 60)
    print("示例2：流式对话")
    print("=" * 60)
    
    config = ChatBotConfig(
        app_id="demo_app",
        app_secret="demo_secret_key",
        base_url="http://localhost:8000",
    )
    
    client = ChatBotSDK(config)
    client.initialize()
    
    print("\n[问题] 请生成一份Python入门教程大纲")
    print("\n[回复] ", end="", flush=True)
    
    for chunk in client.chat(
        message="请生成一份Python入门教程大纲",
        stream=True
    ):
        if chunk.get("type") == "text":
            print(chunk.get("content"), end="", flush=True)
        elif chunk.get("type") == "thought":
            print(f"\n💭 {chunk.get('content')}")
    
    print("\n")


# ==================== 示例3：RAG知识库 ====================

def example_rag_integration():
    """示例3：上传文档到RAG知识库"""
    print("\n" + "=" * 60)
    print("示例3：RAG知识库集成")
    print("=" * 60)
    
    config = ChatBotConfig(
        app_id="demo_app",
        app_secret="demo_secret_key",
        base_url="http://localhost:8000",
        rag_config={
            "chunk_size": 500,
            "top_k": 3
        }
    )
    
    client = ChatBotSDK(config)
    client.initialize()
    
    # 上传产品文档
    print("\n[1] 上传产品文档...")
    doc_content = """
# 产品功能说明

## 核心功能
1. 用户管理：支持用户注册、登录、权限管理
2. 数据分析：提供实时数据分析和可视化
3. API集成：开放REST API供第三方集成

## 使用指南
- 首次使用请先注册账号
- 管理员可在后台配置系统参数
- 支持导出Excel和PDF报告
"""
    
    result = client.upload_document(
        content=doc_content,
        filename="product_manual.md",
        metadata={"category": "documentation", "version": "1.0"}
    )
    print(f"✓ 上传成功: {result}")
    
    # 基于文档提问
    print("\n[2] 基于知识库提问...")
    response = client.chat(
        message="如何导出报告？",
        use_rag=True
    )
    print(f"\n回复: {response}")


# ==================== 示例4：@路径引用 ====================

def example_path_reference():
    """示例4：使用@路径引用本地文件"""
    print("\n" + "=" * 60)
    print("示例4：@路径引用")
    print("=" * 60)
    
    config = ChatBotConfig(
        app_id="demo_app",
        app_secret="demo_secret_key",
        base_url="http://localhost:8000",
        workspace_root="/path/to/your/project"  # 设置工作区根目录
    )
    
    client = ChatBotSDK(config)
    client.initialize()
    
    # 引用项目文件
    print("\n[问题] 请分析 @/backend/app/main.py 的代码结构")
    response = client.chat(
        message="请分析 @/backend/app/main.py 的代码结构"
    )
    print(f"\n回复: {response}")


# ==================== 示例5：自定义工具 ====================

def example_custom_tools():
    """示例5：注册自定义MCP工具"""
    print("\n" + "=" * 60)
    print("示例5：注册自定义工具")
    print("=" * 60)
    
    config = ChatBotConfig(
        app_id="demo_app",
        app_secret="demo_secret_key",
        base_url="http://localhost:8000",
    )
    
    client = ChatBotSDK(config)
    client.initialize()
    
    # 注册自定义工具
    print("\n[1] 注册工具: query_database")
    result = client.register_tool(
        name="query_database",
        description="查询业务数据库",
        parameters={
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "SQL查询语句"
                }
            },
            "required": ["sql"]
        },
        endpoint="https://your-app.com/api/db/query",
        auth={"type": "bearer", "token": "your_api_token"}
    )
    print(f"✓ 工具注册成功: {result}")
    
    # 列出所有工具
    print("\n[2] 列出所有可用工具...")
    tools = client.list_tools()
    print(f"✓ 可用工具: {tools.get('count')} 个")
    for tool in tools.get('tools', []):
        print(f"  - {tool.get('name')}: {tool.get('description')}")


# ==================== 示例6：嵌入到Web应用 ====================

def example_web_integration():
    """示例6：在FastAPI应用中集成"""
    print("\n" + "=" * 60)
    print("示例6：Web应用集成示例代码")
    print("=" * 60)
    
    code = """
# 在你的FastAPI应用中

from fastapi import FastAPI
from chatbot_sdk import ChatBotSDK, ChatBotConfig

app = FastAPI()

# 初始化ChatBot SDK
chatbot = ChatBotSDK(ChatBotConfig(
    app_id="your_app",
    app_secret="your_secret",
    base_url="http://chatbot-server:8000",
    workspace_root="/app/workspace"
))
chatbot.initialize()

@app.post("/api/support")
async def customer_support(question: str):
    \"\"\"客户支持接口\"\"\"
    response = chatbot.chat(
        message=question,
        use_rag=True  # 使用产品文档库
    )
    return {"answer": response}

@app.post("/api/analysis")
async def data_analysis(request: dict):
    \"\"\"数据分析接口\"\"\"
    # 引用用户上传的数据文件
    response = chatbot.chat(
        message=f"请分析 @/uploads/{request['file_id']} 的数据",
        context={"user_id": request['user_id']}
    )
    return {"analysis": response}
"""
    
    print(code)


# ==================== 示例7：后台任务集成 ====================

def example_background_task():
    """示例7：后台任务/自动化脚本"""
    print("\n" + "=" * 60)
    print("示例7：后台任务集成示例")
    print("=" * 60)
    
    code = """
# 自动化报告生成脚本

from chatbot_sdk import create_client
import schedule
import time

# 创建客户端
client = create_client(
    app_id="automation_bot",
    app_secret="secret",
    mcp_tools=["database", "email"]
)
client.initialize()

def generate_daily_report():
    \"\"\"生成每日报告\"\"\"
    # AI会自动调用数据库查询和邮件发送工具
    response = client.chat(
        message=\"\"\"
        请执行以下任务：
        1. 查询昨天的销售数据
        2. 生成分析报告
        3. 发送邮件给sales@company.com
        \"\"\"
    )
    print(f"报告已生成: {response}")

# 每天早上8点执行
schedule.every().day.at("08:00").do(generate_daily_report)

while True:
    schedule.run_pending()
    time.sleep(60)
"""
    
    print(code)


# ==================== 主函数 ====================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Agentic ChatBot SDK 集成示例")
    parser.add_argument(
        "--example",
        type=str,
        default="all",
        choices=["all", "basic", "stream", "rag", "path", "tools", "web", "bg"],
        help="选择运行的示例"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("Agentic ChatBot SDK 集成示例")
    print("=" * 60)
    print("\n⚠️  请确保后端服务已启动: http://localhost:8000")
    print()
    
    try:
        if args.example in ["all", "basic"]:
            example_basic_chat()
        
        if args.example in ["all", "stream"]:
            example_streaming_chat()
        
        if args.example in ["all", "rag"]:
            example_rag_integration()
        
        if args.example in ["all", "path"]:
            example_path_reference()
        
        if args.example in ["all", "tools"]:
            example_custom_tools()
        
        if args.example == "web":
            example_web_integration()
        
        if args.example == "bg":
            example_background_task()
        
        print("\n" + "=" * 60)
        print("✅ 所有示例运行完成！")
        print("=" * 60)
        print("\n📚 更多文档:")
        print("  - SDK文档: sdk/python/README.md")
        print("  - 集成指南: docs/INTEGRATION_GUIDE.md")
        print("  - API文档: http://localhost:8000/docs")
        print()
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        print("\n请检查:")
        print("  1. 后端服务是否启动")
        print("  2. 配置是否正确")
        print("  3. 网络连接是否正常")

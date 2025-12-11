# -*- coding: utf-8 -*-
"""
Universal Agentic ChatBot - 启动脚本

基于LangChain 1.0实现
"""
import asyncio
import uvicorn
from loguru import logger

from app.main import app
from app.config import settings
from app.llm import get_llm_client, get_embedding_client
from app.rag.langchain_rag import get_rag_system
from app.core.memory import MemoryManager
from app.core.tool_executor import ToolExecutor
from app.core import AgentEngine  # 使用 __init__.py 中的别名 (Orchestrator)
from app.mcp import mcp_registry


async def initialize_system():
    """初始化系统"""
    logger.info("="*60)
    logger.info("🚀 Universal Agentic ChatBot - LangChain 1.0")
    logger.info("="*60)
    
    # 1. 初始化LLM客户端
    logger.info("📝 Initializing LLM client...")
    llm_client = get_llm_client()
    logger.info(f"✅ LLM client ready: {llm_client.model}")
    
    # 2. 初始化Embedding客户端
    logger.info("🔢 Initializing Embedding client...")
    embedding_client = get_embedding_client()
    logger.info(f"✅ Embedding client ready: {embedding_client.model}")
    
    # 3. 初始化RAG系统
    logger.info("📚 Initializing RAG system...")
    rag_system = get_rag_system()
    logger.info(f"✅ RAG system ready: {rag_system.vector_store_type}")
    
    # 4. 加载MCP服务器
    logger.info("🔧 Loading MCP servers...")
    await mcp_registry.load_servers()
    tools = await mcp_registry.get_all_tools()
    logger.info(f"✅ {len(tools)} MCP tools loaded")
    
    # 5. 初始化Agent引擎
    logger.info("🤖 Initializing Agent engine...")
    memory_manager = MemoryManager()
    tool_executor = ToolExecutor(mcp_registry)
    agent_engine = AgentEngine(
        memory_manager=memory_manager,
        tool_executor=tool_executor,
    )
    logger.info("✅ Agent engine ready")
    
    logger.info("="*60)
    logger.info(f"🎉 System initialized successfully!")
    logger.info(f"📍 Server: http://{settings.HOST}:{settings.PORT}")
    logger.info(f"📖 API Docs: http://{settings.HOST}:{settings.PORT}/docs")
    logger.info(f"🎨 Frontend: http://localhost:5173")
    logger.info("="*60)


def main():
    """主函数"""
    # 初始化系统
    asyncio.run(initialize_system())
    
    # 启动FastAPI服务
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()

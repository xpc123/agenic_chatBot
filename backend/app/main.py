"""
FastAPI主应用入口
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
import sys
from datetime import datetime

from .config import settings
from .api import api_router
from .mcp import mcp_registry
from .exceptions import ChatBotException
from .dependencies import health_check


# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    level=settings.LOG_LEVEL,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
)
logger.add(
    settings.LOG_FILE,
    rotation="500 MB",
    retention="10 days",
    level=settings.LOG_LEVEL,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("🚀 Starting Agentic ChatBot...")
    
    # 验证配置
    try:
        from .exceptions import ConfigurationError
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.strip() == "":
            raise ConfigurationError(
                message="OPENAI_API_KEY is not configured",
                config_key="OPENAI_API_KEY"
            )
        logger.info("✅ Configuration validated")
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e.message}")
        raise
    
    # 加载MCP服务器
    try:
        await mcp_registry.load_servers()
        logger.info("✅ MCP servers loaded")
    except Exception as e:
        logger.warning(f"Failed to load some MCP servers: {e}")
    
    logger.info("✅ Application started successfully")
    
    yield
    
    # 关闭时执行
    logger.info("👋 Shutting down...")
    
    # 清理资源
    try:
        # 关闭MCP服务器连接
        if hasattr(mcp_registry, 'close_all'):
            await mcp_registry.close_all()
        logger.info("✅ Resources cleaned up")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="通用智能对话机器人框架 - 支持Planning、Memory、RAG和MCP工具",
    lifespan=lifespan,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router)


# ==================== 异常处理器 ====================

@app.exception_handler(ChatBotException)
async def chatbot_exception_handler(request: Request, exc: ChatBotException):
    """处理自定义异常"""
    logger.error(f"ChatBot error: {exc.message} | Code: {exc.code} | Details: {exc.details}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=exc.to_dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理未捕获的异常"""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "type": type(exc).__name__,
            }
        }
    )


# ==================== 健康检查端点 ====================

@app.get("/health", tags=["System"])
async def health_check_endpoint():
    """
    健康检查端点
    
    返回系统健康状态，包括各组件的状态
    """
    health_data = await health_check()
    status_code = (
        status.HTTP_200_OK
        if health_data["status"] == "healthy"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    
    health_data["timestamp"] = datetime.utcnow().isoformat()
    health_data["app_name"] = settings.APP_NAME
    health_data["version"] = settings.APP_VERSION
    
    return JSONResponse(
        status_code=status_code,
        content=health_data
    )


@app.get("/", tags=["System"])
async def root():
    """根端点 - 欢迎信息"""
    return {
        "message": "🚀 Welcome to Agentic ChatBot API",
        "description": "通用智能对话机器人平台 - 基于 LangChain 1.0 架构",
        "version": settings.APP_VERSION,
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "chat_api": "/api/v1/chat",
            "rag_api": "/api/v1/documents",
            "tools_api": "/api/v1/tools",
        },
        "features": [
            "智能规划与执行",
            "会话记忆管理",
            "MCP 工具扩展",
            "RAG 文档检索",
            "@路径引用",
        ]
    }


# 静态文件服务 (用于前端)
# app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )

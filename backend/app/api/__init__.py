# -*- coding: utf-8 -*-
"""
API路由模块
"""
from fastapi import APIRouter
from .chat import router as chat_router
from .documents import router as documents_router
from .tools import router as tools_router
from .sdk import sdk_router

# 创建主路由
api_router = APIRouter(prefix="/api/v1")

# 注册子路由
api_router.include_router(chat_router)
api_router.include_router(documents_router)
api_router.include_router(tools_router)
api_router.include_router(sdk_router)

__all__ = ["api_router"]

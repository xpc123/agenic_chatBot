# -*- coding: utf-8 -*-
"""
API v2 - 统一版本 API

所有 API 端点统一在 /api/v2/ 下：
- /api/v2/chat/*       - 聊天相关
- /api/v2/documents/*  - 文档管理
- /api/v2/settings/*   - 设置管理
- /api/v2/tools/*      - 工具管理
- /api/v2/batch/*      - 批量操作
"""
from fastapi import APIRouter

from .chat import router as chat_router
from .documents import router as documents_router
from .settings import router as settings_router
from .tools import router as tools_router
from .batch import router as batch_router

# 创建 v2 主路由
api_v2_router = APIRouter(prefix="/api/v2")

# 注册子路由
api_v2_router.include_router(chat_router)
api_v2_router.include_router(documents_router)
api_v2_router.include_router(settings_router)
api_v2_router.include_router(tools_router)
api_v2_router.include_router(batch_router)

__all__ = ["api_v2_router"]


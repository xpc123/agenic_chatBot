# -*- coding: utf-8 -*-
"""
SDK 异常定义
"""


class AgenticSDKError(Exception):
    """SDK 基础异常"""
    pass


class ConnectionError(AgenticSDKError):
    """连接错误 - 无法连接到后端服务"""
    pass


class AuthenticationError(AgenticSDKError):
    """认证错误 - API Key 无效或权限不足"""
    pass


class APIError(AgenticSDKError):
    """API 错误 - 请求失败"""
    pass


class ValidationError(AgenticSDKError):
    """验证错误 - 参数无效"""
    pass


class TimeoutError(AgenticSDKError):
    """超时错误"""
    pass


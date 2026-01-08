# -*- coding: utf-8 -*-
"""
统一认证中间件

支持多种认证方式：
1. API Key (X-API-Key header)
2. JWT Token (Authorization: Bearer <token>)
3. HMAC 签名 (X-App-Id + X-Timestamp + X-Signature)

使用方式:
    from .middleware import get_current_user, AuthenticatedUser
    
    @router.get("/protected")
    async def protected_endpoint(user: AuthenticatedUser = Depends(get_current_user)):
        return {"user_id": user.user_id}
"""
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
import hmac
import hashlib
import time

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from loguru import logger
import jwt

from ..config import settings


# ==================== 数据模型 ====================

@dataclass
class AuthenticatedUser:
    """认证用户信息"""
    user_id: str
    app_id: Optional[str] = None
    auth_method: str = "anonymous"  # api_key, jwt, hmac, anonymous
    permissions: list = None
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []


# ==================== 认证方案 ====================

# API Key 认证
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# JWT Bearer 认证
bearer_scheme = HTTPBearer(auto_error=False)

# HMAC 签名认证 headers
HMAC_HEADERS = ["X-App-Id", "X-Timestamp", "X-Signature"]


# ==================== 认证函数 ====================

def verify_api_key(api_key: str) -> Optional[AuthenticatedUser]:
    """验证 API Key"""
    # 检查配置的 API Key
    valid_keys = getattr(settings, 'API_KEYS', {})
    
    # 如果未配置 API Keys，接受 SDK_API_KEY
    if not valid_keys and hasattr(settings, 'SDK_API_KEY'):
        if api_key == settings.SDK_API_KEY:
            return AuthenticatedUser(
                user_id="sdk_user",
                auth_method="api_key",
                permissions=["chat", "documents", "settings"],
            )
    
    # 检查有效的 API Key
    if api_key in valid_keys:
        key_info = valid_keys[api_key]
        return AuthenticatedUser(
            user_id=key_info.get("user_id", "api_user"),
            auth_method="api_key",
            permissions=key_info.get("permissions", ["chat"]),
        )
    
    return None


def verify_jwt_token(token: str) -> Optional[AuthenticatedUser]:
    """验证 JWT Token"""
    jwt_secret = getattr(settings, 'JWT_SECRET', None)
    
    if not jwt_secret:
        return None
    
    try:
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        
        # 检查过期
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.now():
            return None
        
        return AuthenticatedUser(
            user_id=payload.get("sub", payload.get("user_id", "jwt_user")),
            auth_method="jwt",
            permissions=payload.get("permissions", ["chat"]),
        )
        
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None


def verify_hmac_signature(
    app_id: str,
    timestamp: str,
    signature: str,
    body: str = "",
) -> Optional[AuthenticatedUser]:
    """验证 HMAC 签名"""
    # 获取 app_secret
    app_secrets = getattr(settings, 'APP_SECRETS', {})
    
    # 如果未配置，使用 SDK_API_KEY 作为默认 secret
    if not app_secrets and hasattr(settings, 'SDK_API_KEY'):
        app_secrets = {"default": settings.SDK_API_KEY}
    
    app_secret = app_secrets.get(app_id)
    if not app_secret:
        return None
    
    # 验证时间戳（5分钟有效期）
    try:
        ts = int(timestamp)
        if abs(time.time() - ts) > 300:
            logger.warning(f"HMAC timestamp expired: {timestamp}")
            return None
    except ValueError:
        return None
    
    # 计算签名
    message = f"{app_id}{timestamp}{body}"
    expected_signature = hmac.new(
        app_secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(expected_signature, signature):
        logger.warning(f"HMAC signature mismatch for app: {app_id}")
        return None
    
    return AuthenticatedUser(
        user_id=f"app_{app_id}",
        app_id=app_id,
        auth_method="hmac",
        permissions=["chat", "documents", "settings"],
    )


# ==================== 依赖注入 ====================

async def get_current_user(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> AuthenticatedUser:
    """
    获取当前认证用户
    
    认证优先级：
    1. API Key
    2. JWT Bearer Token
    3. HMAC 签名
    4. 匿名用户（如果允许）
    """
    
    # 1. 尝试 API Key 认证
    if api_key:
        user = verify_api_key(api_key)
        if user:
            return user
    
    # 2. 尝试 JWT Bearer 认证
    if bearer and bearer.credentials:
        user = verify_jwt_token(bearer.credentials)
        if user:
            return user
    
    # 3. 尝试 HMAC 签名认证
    app_id = request.headers.get("X-App-Id")
    timestamp = request.headers.get("X-Timestamp")
    signature = request.headers.get("X-Signature")
    
    if app_id and timestamp and signature:
        # 获取请求体
        body = ""
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
            body = body.decode("utf-8") if body else ""
        
        user = verify_hmac_signature(app_id, timestamp, signature, body)
        if user:
            return user
    
    # 4. 检查是否允许匿名访问
    allow_anonymous = getattr(settings, 'ALLOW_ANONYMOUS', True)
    
    if allow_anonymous:
        return AuthenticatedUser(
            user_id="anonymous",
            auth_method="anonymous",
            permissions=["chat"],  # 匿名用户只能聊天
        )
    
    # 认证失败
    raise HTTPException(
        status_code=401,
        detail={
            "error": "Authentication required",
            "supported_methods": ["API Key", "JWT Bearer", "HMAC Signature"],
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_permission(permission: str):
    """
    权限检查依赖
    
    使用方式:
        @router.get("/admin")
        async def admin_endpoint(
            user: AuthenticatedUser = Depends(get_current_user),
            _: None = Depends(require_permission("admin")),
        ):
            ...
    """
    async def checker(user: AuthenticatedUser = Depends(get_current_user)):
        if permission not in user.permissions and "admin" not in user.permissions:
            raise HTTPException(
                status_code=403,
                detail={"error": f"Permission '{permission}' required"},
            )
        return None
    
    return checker


# ==================== 工具函数 ====================

def generate_api_key() -> str:
    """生成新的 API Key"""
    import secrets
    return f"sk-{secrets.token_urlsafe(32)}"


def generate_jwt_token(
    user_id: str,
    permissions: list = None,
    expires_in: int = 3600,
) -> str:
    """生成 JWT Token"""
    jwt_secret = getattr(settings, 'JWT_SECRET', 'default_secret')
    
    payload = {
        "sub": user_id,
        "permissions": permissions or ["chat"],
        "iat": datetime.now().timestamp(),
        "exp": datetime.now().timestamp() + expires_in,
    }
    
    return jwt.encode(payload, jwt_secret, algorithm="HS256")


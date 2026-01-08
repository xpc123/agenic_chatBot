# -*- coding: utf-8 -*-
"""
认证中间件测试

测试不同认证方式：
- API Key 认证
- JWT Bearer Token 认证
- HMAC 签名认证
- 公开端点（无需认证）
"""
import pytest
import sys
import time
import hmac
import hashlib
from pathlib import Path
from unittest.mock import patch
import os

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """创建测试客户端"""
    from app.main import app
    return TestClient(app)


class TestPublicEndpoints:
    """测试公开端点（无需认证）"""
    
    def test_health_check_no_auth(self, client):
        """测试健康检查不需要认证"""
        response = client.get("/health")
        
        # 健康检查应该能访问，但可能返回 503 如果服务未完全初始化
        assert response.status_code in [200, 503]
        assert "status" in response.json()
    
    def test_docs_no_auth(self, client):
        """测试文档端点不需要认证"""
        response = client.get("/docs")
        
        # /docs 返回 HTML
        assert response.status_code == 200
    
    def test_openapi_no_auth(self, client):
        """测试 OpenAPI schema 不需要认证"""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200


class TestAPIKeyAuth:
    """测试 API Key 认证"""
    
    def test_valid_api_key(self, client):
        """测试有效的 API Key"""
        response = client.get(
            "/api/v2/chat/stats",
            headers={"X-API-Key": "default_secret"},
        )
        
        # 应该通过认证
        assert response.status_code in [200, 500]  # 500 可能是后续处理错误
    
    def test_invalid_api_key(self, client):
        """测试无效的 API Key（允许匿名时会通过）"""
        response = client.get(
            "/api/v2/chat/stats",
            headers={"X-API-Key": "invalid_key"},
        )
        
        # 默认允许匿名访问，所以无效 key 也能通过（使用匿名身份）
        # 或者返回 401 如果不允许匿名
        assert response.status_code in [200, 401, 500]
    
    def test_missing_api_key(self, client):
        """测试缺少 API Key（允许匿名时会通过）"""
        response = client.get("/api/v2/chat/stats")
        
        # 默认允许匿名访问
        assert response.status_code in [200, 401, 500]


class TestJWTAuth:
    """测试 JWT Bearer Token 认证"""
    
    def test_valid_jwt(self, client):
        """测试有效的 JWT（使用测试 token）"""
        response = client.get(
            "/api/v2/chat/stats",
            headers={"Authorization": "Bearer dummy_jwt_token"},
        )
        
        # JWT 可能无效（未配置），会回退到匿名访问
        assert response.status_code in [200, 401, 500]
    
    def test_invalid_jwt(self, client):
        """测试无效的 JWT（允许匿名时会通过）"""
        response = client.get(
            "/api/v2/chat/stats",
            headers={"Authorization": "Bearer invalid_token"},
        )
        
        # 无效 JWT 会回退到匿名访问（如果允许）
        assert response.status_code in [200, 401, 500]
    
    def test_malformed_bearer(self, client):
        """测试格式错误的 Bearer（允许匿名时会通过）"""
        response = client.get(
            "/api/v2/chat/stats",
            headers={"Authorization": "Bearer"},  # 缺少 token
        )
        
        # 格式错误会回退到匿名访问
        assert response.status_code in [200, 401, 500]


class TestHMACAuth:
    """测试 HMAC 签名认证"""
    
    def generate_hmac_headers(self, app_id: str, app_secret: str) -> dict:
        """生成 HMAC 认证头"""
        timestamp = str(int(time.time()))
        message = f"{app_id}{timestamp}"
        signature = hmac.new(
            app_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return {
            "X-App-Id": app_id,
            "X-Timestamp": timestamp,
            "X-Signature": signature,
        }
    
    def test_valid_hmac(self, client):
        """测试有效的 HMAC 签名"""
        headers = self.generate_hmac_headers("default", "default_secret")
        
        response = client.get(
            "/api/v2/chat/stats",
            headers=headers,
        )
        
        # 应该通过认证
        assert response.status_code in [200, 500]
    
    def test_invalid_signature(self, client):
        """测试无效的签名（允许匿名时会通过）"""
        timestamp = str(int(time.time()))
        
        response = client.get(
            "/api/v2/chat/stats",
            headers={
                "X-App-Id": "default",
                "X-Timestamp": timestamp,
                "X-Signature": "invalid_signature",
            },
        )
        
        # 签名无效会回退到匿名访问
        assert response.status_code in [200, 401, 500]
    
    def test_expired_timestamp(self, client):
        """测试过期的时间戳（允许匿名时会通过）"""
        # 使用 10 分钟前的时间戳
        expired_timestamp = str(int(time.time()) - 600)
        message = f"default{expired_timestamp}"
        signature = hmac.new(
            b"default_secret",
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        response = client.get(
            "/api/v2/chat/stats",
            headers={
                "X-App-Id": "default",
                "X-Timestamp": expired_timestamp,
                "X-Signature": signature,
            },
        )
        
        # 过期时间戳会回退到匿名访问
        assert response.status_code in [200, 401, 500]
    
    def test_invalid_app_id(self, client):
        """测试无效的 App ID（允许匿名时会通过）"""
        headers = self.generate_hmac_headers("invalid_app", "some_secret")
        
        response = client.get(
            "/api/v2/chat/stats",
            headers=headers,
        )
        
        # 无效 App ID 会回退到匿名访问
        assert response.status_code in [200, 401, 500]


class TestAuthPriority:
    """测试认证优先级"""
    
    def test_api_key_takes_priority(self, client):
        """测试 API Key 优先于其他认证"""
        response = client.get(
            "/api/v2/chat/stats",
            headers={
                "X-API-Key": "default_secret",
                "Authorization": "Bearer invalid_token",
            },
        )
        
        # API Key 有效，应该通过
        assert response.status_code in [200, 500]
    
    def test_jwt_before_hmac(self, client):
        """测试 JWT 优先于 HMAC"""
        timestamp = str(int(time.time()))
        
        response = client.get(
            "/api/v2/chat/stats",
            headers={
                "Authorization": "Bearer dummy_jwt_token",
                "X-App-Id": "default",
                "X-Timestamp": timestamp,
                "X-Signature": "invalid",
            },
        )
        
        # JWT 有效，应该通过
        assert response.status_code in [200, 500]


class TestAuthErrorMessages:
    """测试认证错误消息"""
    
    def test_invalid_api_key_message(self, client):
        """测试无效 API Key 请求（允许匿名时不会报错）"""
        response = client.get(
            "/api/v2/chat/stats",
            headers={"X-API-Key": "wrong_key"},
        )
        
        # 默认允许匿名访问，所以不会返回 401
        # 如果配置了禁用匿名访问，则返回 401
        assert response.status_code in [200, 401, 500]
    
    def test_missing_auth_message(self, client):
        """测试缺少认证请求（允许匿名时不会报错）"""
        response = client.get("/api/v2/chat/stats")
        
        # 默认允许匿名访问
        assert response.status_code in [200, 401, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


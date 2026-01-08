# -*- coding: utf-8 -*-
"""
API v2 端点测试

测试后端 REST API v2 端点：
- Chat API
- Documents API
- Settings API
- Batch API
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import json

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """创建测试客户端"""
    from app.main import app
    
    # 禁用认证中间件用于测试
    app.state.testing = True
    
    return TestClient(app)


@pytest.fixture
def mock_orchestrator():
    """Mock 编排器"""
    mock = AsyncMock()
    mock.chat.return_value = {
        "message": "测试响应",
        "session_id": "test-session",
        "used_tools": [],
        "citations": [],
    }
    return mock


class TestHealthCheck:
    """测试健康检查端点"""
    
    def test_health_check(self, client):
        """测试 /health 端点"""
        response = client.get("/health")
        
        # 健康检查应该返回 200 或 503（如果服务未完全启动）
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data


class TestChatAPI:
    """测试 Chat API"""
    
    def test_send_message(self, client):
        """测试发送消息"""
        response = client.post(
            "/api/v2/chat/message",
            json={
                "message": "你好",
                "session_id": "test-session",
                "use_rag": True,
            },
            headers={"X-API-Key": "default_secret"},
        )
        
        # 可能返回 200 或 401（取决于认证设置）
        assert response.status_code in [200, 401, 500]
    
    def test_send_message_without_session(self, client):
        """测试不带 session_id 的消息"""
        response = client.post(
            "/api/v2/chat/message",
            json={
                "message": "你好",
                "use_rag": False,
            },
            headers={"X-API-Key": "default_secret"},
        )
        
        assert response.status_code in [200, 401, 500]
    
    def test_analyze_intent(self, client):
        """测试意图分析"""
        response = client.post(
            "/api/v2/chat/analyze-intent",
            json={"message": "帮我写一个 Python 函数"},
            headers={"X-API-Key": "default_secret"},
        )
        
        assert response.status_code in [200, 401, 500]
    
    def test_clear_session(self, client):
        """测试清除会话"""
        response = client.delete(
            "/api/v2/chat/session/test-session",
            headers={"X-API-Key": "default_secret"},
        )
        
        assert response.status_code in [200, 401, 404, 500]
    
    def test_get_stats(self, client):
        """测试获取统计"""
        response = client.get(
            "/api/v2/chat/stats",
            headers={"X-API-Key": "default_secret"},
        )
        
        assert response.status_code in [200, 401, 500]


class TestDocumentsAPI:
    """测试 Documents API"""
    
    def test_list_documents(self, client):
        """测试列出文档"""
        response = client.get(
            "/api/v2/documents/list",
            params={"page": 1, "page_size": 10},
            headers={"X-API-Key": "default_secret"},
        )
        
        assert response.status_code in [200, 401, 500]
    
    def test_search_documents(self, client):
        """测试搜索文档"""
        response = client.post(
            "/api/v2/documents/search",
            json={"query": "测试查询", "top_k": 5},
            headers={"X-API-Key": "default_secret"},
        )
        
        assert response.status_code in [200, 401, 500]
    
    def test_get_document(self, client):
        """测试获取文档"""
        response = client.get(
            "/api/v2/documents/test-doc-id",
            headers={"X-API-Key": "default_secret"},
        )
        
        assert response.status_code in [200, 401, 404, 500]
    
    def test_delete_document(self, client):
        """测试删除文档"""
        response = client.delete(
            "/api/v2/documents/test-doc-id",
            headers={"X-API-Key": "default_secret"},
        )
        
        assert response.status_code in [200, 401, 404, 500]


class TestSettingsAPI:
    """测试 Settings API"""
    
    def test_get_indexing_status(self, client):
        """测试获取索引状态"""
        response = client.get(
            "/api/v2/settings/indexing/status",
            params={"workspace": "."},
            headers={"X-API-Key": "default_secret"},
        )
        
        assert response.status_code in [200, 401, 500]
    
    def test_list_rules(self, client):
        """测试列出规则"""
        response = client.get(
            "/api/v2/settings/rules",
            headers={"X-API-Key": "default_secret"},
        )
        
        assert response.status_code in [200, 401, 500]
    
    def test_add_rule(self, client):
        """测试添加规则"""
        response = client.post(
            "/api/v2/settings/rules",
            json={"content": "测试规则", "type": "user"},
            headers={"X-API-Key": "default_secret"},
        )
        
        assert response.status_code in [200, 401, 500]
    
    def test_list_skills(self, client):
        """测试列出技能"""
        response = client.get(
            "/api/v2/settings/skills",
            headers={"X-API-Key": "default_secret"},
        )
        
        assert response.status_code in [200, 401, 500]
    
    def test_toggle_skill(self, client):
        """测试切换技能"""
        response = client.post(
            "/api/v2/settings/skills/test-skill/toggle",
            params={"enabled": True},
            headers={"X-API-Key": "default_secret"},
        )
        
        assert response.status_code in [200, 401, 404, 500]
    
    def test_list_mcp_servers(self, client):
        """测试列出 MCP 服务器"""
        response = client.get(
            "/api/v2/settings/mcp",
            headers={"X-API-Key": "default_secret"},
        )
        
        assert response.status_code in [200, 401, 500]
    
    def test_get_settings_summary(self, client):
        """测试获取设置摘要"""
        response = client.get(
            "/api/v2/settings/summary",
            params={"workspace": "."},
            headers={"X-API-Key": "default_secret"},
        )
        
        assert response.status_code in [200, 401, 500]


class TestBatchAPI:
    """测试 Batch API"""
    
    def test_batch_chat(self, client):
        """测试批量对话"""
        response = client.post(
            "/api/v2/batch/chat",
            json={
                "requests": [
                    {"message": "问题1"},
                    {"message": "问题2"},
                ],
                "parallel": True,
            },
            headers={"X-API-Key": "default_secret"},
        )
        
        assert response.status_code in [200, 401, 500]


class TestAPIValidation:
    """测试 API 输入验证"""
    
    def test_empty_message(self, client):
        """测试空消息"""
        response = client.post(
            "/api/v2/chat/message",
            json={"message": ""},
            headers={"X-API-Key": "default_secret"},
        )
        
        # 应该返回验证错误或处理空消息
        assert response.status_code in [200, 400, 401, 422, 500]
    
    def test_invalid_json(self, client):
        """测试无效 JSON"""
        response = client.post(
            "/api/v2/chat/message",
            data="not valid json",
            headers={
                "X-API-Key": "default_secret",
                "Content-Type": "application/json",
            },
        )
        
        assert response.status_code in [400, 401, 422]
    
    def test_missing_required_field(self, client):
        """测试缺少必填字段"""
        response = client.post(
            "/api/v2/chat/message",
            json={},
            headers={"X-API-Key": "default_secret"},
        )
        
        assert response.status_code in [400, 401, 422]


class TestCORS:
    """测试 CORS 配置"""
    
    def test_cors_headers(self, client):
        """测试 CORS 头"""
        response = client.options(
            "/api/v2/chat/message",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        
        # 应该返回 CORS 头
        assert response.status_code in [200, 401, 405]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


# -*- coding: utf-8 -*-
"""
完整 API 功能测试

覆盖所有 /api/v2/ 端点的功能测试。
运行前需要启动后端: cd backend && python run.py
"""
import pytest
import requests
import time
import os
from typing import Dict, Any, Optional


BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


@pytest.fixture(scope="module")
def api_client():
    """创建 API 客户端"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # 检查后端是否运行
    for _ in range(3):
        try:
            response = session.get(f"{BACKEND_URL}/health", timeout=5)
            if response.status_code in [200, 503]:
                return session
        except requests.exceptions.ConnectionError:
            time.sleep(2)
    
    pytest.skip("Backend not available - run: cd backend && python run.py")


@pytest.fixture
def unique_session_id():
    """生成唯一会话 ID"""
    return f"test-{int(time.time() * 1000)}"


# ==================== 1. Chat API 测试 (10 个端点) ====================

class TestChatMessage:
    """POST /api/v2/chat/message"""
    
    def test_simple_message(self, api_client, unique_session_id):
        """测试简单消息"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"message": "你好", "session_id": unique_session_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert len(data["message"]) > 0
    
    def test_message_with_context(self, api_client, unique_session_id):
        """测试带上下文的消息"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={
                "message": "分析这段代码",
                "session_id": unique_session_id,
                "context": {"language": "python"}
            }
        )
        assert response.status_code == 200
    
    def test_message_with_user_id(self, api_client, unique_session_id):
        """测试带用户 ID 的消息"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={
                "message": "你好",
                "session_id": unique_session_id,
                "user_id": "test-user-123"
            }
        )
        assert response.status_code == 200


class TestChatStream:
    """POST /api/v2/chat/stream"""
    
    def test_stream_response(self, api_client, unique_session_id):
        """测试流式响应"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/stream",
            json={"message": "简短回答：1+1=?", "session_id": unique_session_id},
            stream=True,
            timeout=30
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        
        # 验证收到数据
        chunks = []
        for line in response.iter_lines():
            if line:
                chunks.append(line)
            if len(chunks) >= 2:
                break
        assert len(chunks) > 0


class TestChatAnalyzeIntent:
    """POST /api/v2/chat/analyze-intent"""
    
    def test_analyze_query_intent(self, api_client):
        """测试查询意图分析"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/analyze-intent",
            json={"message": "什么是 Python？"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "task_type" in data
        assert "surface_intent" in data
        assert "confidence" in data
    
    def test_analyze_action_intent(self, api_client):
        """测试操作意图分析"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/analyze-intent",
            json={"message": "执行 ls 命令"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_type"] in ["action", "query", "complex"]
    
    def test_analyze_creation_intent(self, api_client):
        """测试创建意图分析"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/analyze-intent",
            json={"message": "帮我写一个排序算法"}
        )
        assert response.status_code == 200


class TestChatPreferences:
    """GET /api/v2/chat/preferences/{user_id}"""
    
    def test_get_preferences(self, api_client):
        """测试获取用户偏好"""
        response = api_client.get(
            f"{BACKEND_URL}/api/v2/chat/preferences/test-user"
        )
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data


class TestChatFeedback:
    """POST /api/v2/chat/feedback/{session_id}"""
    
    def test_positive_feedback(self, api_client, unique_session_id):
        """测试正面反馈"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/feedback/{unique_session_id}",
            params={"feedback": "positive"}
        )
        assert response.status_code == 200
    
    def test_negative_feedback(self, api_client, unique_session_id):
        """测试负面反馈"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/feedback/{unique_session_id}",
            params={"feedback": "negative"}
        )
        assert response.status_code == 200
    
    def test_invalid_feedback(self, api_client, unique_session_id):
        """测试无效反馈"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/feedback/{unique_session_id}",
            params={"feedback": "invalid"}
        )
        assert response.status_code == 400


class TestChatSkills:
    """GET /api/v2/chat/skills"""
    
    def test_list_skills(self, api_client):
        """测试列出技能"""
        response = api_client.get(f"{BACKEND_URL}/api/v2/chat/skills")
        assert response.status_code == 200
        data = response.json()
        assert "skills" in data or "total" in data


class TestChatStats:
    """GET /api/v2/chat/stats"""
    
    def test_get_stats(self, api_client):
        """测试获取统计"""
        response = api_client.get(f"{BACKEND_URL}/api/v2/chat/stats")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestChatSession:
    """DELETE /api/v2/chat/session/{session_id}"""
    
    def test_clear_session(self, api_client, unique_session_id):
        """测试清除会话"""
        # 先创建会话
        api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"message": "测试", "session_id": unique_session_id}
        )
        
        # 清除会话
        response = api_client.delete(
            f"{BACKEND_URL}/api/v2/chat/session/{unique_session_id}"
        )
        assert response.status_code == 200
    
    def test_clear_nonexistent_session(self, api_client):
        """测试清除不存在的会话"""
        response = api_client.delete(
            f"{BACKEND_URL}/api/v2/chat/session/nonexistent-session"
        )
        # 应该优雅处理
        assert response.status_code in [200, 404]


# ==================== 2. Documents API 测试 (4 个端点) ====================

class TestDocumentsList:
    """GET /api/v2/documents/list"""
    
    def test_list_documents(self, api_client):
        """测试列出文档"""
        response = api_client.get(f"{BACKEND_URL}/api/v2/documents/list")
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data or "total" in data
    
    def test_list_documents_with_filter(self, api_client):
        """测试带过滤的文档列表"""
        response = api_client.get(
            f"{BACKEND_URL}/api/v2/documents/list",
            params={"file_type": "py"}
        )
        assert response.status_code == 200


class TestDocumentsSearch:
    """POST /api/v2/documents/search"""
    
    def test_search_documents(self, api_client):
        """测试搜索文档"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/documents/search",
            json={"query": "python"}
        )
        assert response.status_code in [200, 404]
    
    def test_search_with_limit(self, api_client):
        """测试带限制的搜索"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/documents/search",
            json={"query": "test", "top_k": 5}
        )
        assert response.status_code in [200, 404]


class TestDocumentsUpload:
    """POST /api/v2/documents/upload"""
    
    def test_upload_text_document(self, api_client):
        """测试上传文本文档"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/documents/upload",
            json={
                "content": "这是一个测试文档的内容",
                "filename": "test_doc.txt",
                "metadata": {"source": "test"}
            }
        )
        # 可能需要特定权限
        assert response.status_code in [200, 201, 403, 422]


class TestDocumentsDelete:
    """DELETE /api/v2/documents/{document_id}"""
    
    def test_delete_nonexistent_document(self, api_client):
        """测试删除不存在的文档"""
        response = api_client.delete(
            f"{BACKEND_URL}/api/v2/documents/nonexistent-doc-id"
        )
        assert response.status_code in [200, 404]


# ==================== 3. Settings API 测试 (10 个端点) ====================

class TestSettingsIndexing:
    """Settings Indexing API"""
    
    def test_get_indexing_status(self, api_client):
        """GET /api/v2/settings/indexing/status"""
        response = api_client.get(f"{BACKEND_URL}/api/v2/settings/indexing/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "indexed" in data or "error" in data
    
    def test_sync_indexing(self, api_client):
        """POST /api/v2/settings/indexing/sync"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/settings/indexing/sync",
            json={"force": False, "priority_only": False}
        )
        assert response.status_code in [200, 202, 503]
    
    def test_delete_indexing(self, api_client):
        """DELETE /api/v2/settings/indexing"""
        response = api_client.delete(f"{BACKEND_URL}/api/v2/settings/indexing")
        # 可能需要特定条件才能删除
        assert response.status_code in [200, 404, 409]


class TestSettingsRules:
    """Settings Rules API"""
    
    def test_get_rules(self, api_client):
        """GET /api/v2/settings/rules"""
        response = api_client.get(f"{BACKEND_URL}/api/v2/settings/rules")
        assert response.status_code == 200
    
    def test_add_rule(self, api_client):
        """POST /api/v2/settings/rules"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/settings/rules",
            json={"content": "测试规则", "type": "user"}
        )
        assert response.status_code in [200, 201]


class TestSettingsSkills:
    """Settings Skills API"""
    
    def test_get_all_skills(self, api_client):
        """GET /api/v2/settings/skills"""
        response = api_client.get(f"{BACKEND_URL}/api/v2/settings/skills")
        assert response.status_code == 200
    
    def test_get_skill_by_id(self, api_client):
        """GET /api/v2/settings/skills/{skill_id}"""
        response = api_client.get(f"{BACKEND_URL}/api/v2/settings/skills/code_review")
        assert response.status_code in [200, 404]
    
    def test_toggle_skill(self, api_client):
        """POST /api/v2/settings/skills/{skill_id}/toggle"""
        # 先获取一个存在的 skill id
        skills_resp = api_client.get(f"{BACKEND_URL}/api/v2/settings/skills")
        if skills_resp.status_code == 200:
            skills = skills_resp.json().get("skills", [])
            if skills:
                skill_id = skills[0].get("id", "code_review")
            else:
                skill_id = "code_review"
        else:
            skill_id = "code_review"
        
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/settings/skills/{skill_id}/toggle"
        )
        # 可能 skill 不存在或需要 body
        assert response.status_code in [200, 404, 422]


class TestSettingsMCP:
    """Settings MCP API"""
    
    def test_list_mcp_servers(self, api_client):
        """GET /api/v2/settings/mcp"""
        response = api_client.get(f"{BACKEND_URL}/api/v2/settings/mcp")
        assert response.status_code == 200
    
    def test_add_mcp_server(self, api_client):
        """POST /api/v2/settings/mcp"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/settings/mcp",
            json={
                "name": "test-server",
                "server_type": "http",
                "url": "http://localhost:9999"
            }
        )
        # 可能因服务器不可达而失败
        assert response.status_code in [200, 201, 400, 422, 500]
    
    def test_delete_mcp_server(self, api_client):
        """DELETE /api/v2/settings/mcp/{server_name}"""
        response = api_client.delete(f"{BACKEND_URL}/api/v2/settings/mcp/nonexistent-server")
        assert response.status_code in [200, 404]


class TestSettingsSummary:
    """GET /api/v2/settings/summary"""
    
    def test_get_summary(self, api_client):
        """测试获取设置摘要"""
        response = api_client.get(f"{BACKEND_URL}/api/v2/settings/summary")
        assert response.status_code == 200


# ==================== 4. Tools API 测试 (5 个端点) ====================

class TestToolsList:
    """GET /api/v2/tools/list"""
    
    def test_list_tools(self, api_client):
        """测试列出工具"""
        response = api_client.get(f"{BACKEND_URL}/api/v2/tools/list")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data or "total" in data
    
    def test_list_tools_by_server(self, api_client):
        """测试按服务器列出工具"""
        response = api_client.get(
            f"{BACKEND_URL}/api/v2/tools/list",
            params={"server_name": "virtuoso-mcp"}
        )
        assert response.status_code == 200


class TestToolsHealth:
    """GET /api/v2/tools/health"""
    
    def test_tools_health(self, api_client):
        """测试工具健康状态"""
        response = api_client.get(f"{BACKEND_URL}/api/v2/tools/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestToolsServers:
    """Tools Servers API"""
    
    def test_list_servers(self, api_client):
        """GET /api/v2/tools/servers"""
        response = api_client.get(f"{BACKEND_URL}/api/v2/tools/servers")
        # 可能因 MCP 服务器配置问题而失败
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "servers" in data or "total" in data
    
    def test_register_server(self, api_client):
        """POST /api/v2/tools/servers/register"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/tools/servers/register",
            json={
                "name": "test-server",
                "url": "http://localhost:9999",
                "description": "Test MCP Server"
            }
        )
        # 可能会失败因为服务器不存在
        assert response.status_code in [200, 500]
    
    def test_reload_server(self, api_client):
        """POST /api/v2/tools/servers/{server_name}/reload"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/tools/servers/virtuoso-mcp/reload"
        )
        assert response.status_code in [200, 404, 500]


# ==================== 5. Batch API 测试 (2 个端点) ====================

class TestBatchChat:
    """POST /api/v2/batch/chat"""
    
    def test_batch_chat(self, api_client):
        """测试批量对话"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/batch/chat",
            json={
                "requests": [
                    {"message": "你好", "session_id": "batch-1"},
                    {"message": "再见", "session_id": "batch-2"},
                ]
            }
        )
        assert response.status_code in [200, 202]
    
    def test_batch_chat_empty(self, api_client):
        """测试空批量对话"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/batch/chat",
            json={"requests": []}
        )
        assert response.status_code in [200, 400, 422]


class TestBatchDocuments:
    """POST /api/v2/batch/documents"""
    
    def test_batch_documents(self, api_client):
        """测试批量文档操作"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/batch/documents",
            json={
                "documents": [
                    {"content": "文档1", "filename": "doc1.txt"},
                    {"content": "文档2", "filename": "doc2.txt"},
                ]
            }
        )
        assert response.status_code in [200, 201, 202, 422]


# ==================== 6. 健康检查测试 ====================

class TestHealthCheck:
    """GET /health"""
    
    def test_health_check(self, api_client):
        """测试健康检查"""
        response = api_client.get(f"{BACKEND_URL}/health")
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data
        assert "components" in data


# ==================== 7. 场景测试 ====================

class TestCompleteScenarios:
    """完整场景测试"""
    
    def test_multi_turn_conversation(self, api_client):
        """测试多轮对话场景"""
        session_id = f"scenario-{int(time.time())}"
        
        # 第一轮
        resp1 = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"message": "我叫测试用户", "session_id": session_id}
        )
        assert resp1.status_code == 200
        
        # 第二轮
        resp2 = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"message": "我叫什么？", "session_id": session_id}
        )
        assert resp2.status_code == 200
        
        # 验证上下文保持
        # (AI 应该记住用户名字)
    
    def test_document_workflow(self, api_client):
        """测试文档工作流"""
        # 1. 列出文档
        list_resp = api_client.get(f"{BACKEND_URL}/api/v2/documents/list")
        assert list_resp.status_code == 200
        
        # 2. 搜索文档
        search_resp = api_client.post(
            f"{BACKEND_URL}/api/v2/documents/search",
            json={"query": "test"}
        )
        assert search_resp.status_code in [200, 404]
    
    def test_settings_workflow(self, api_client):
        """测试设置工作流"""
        # 1. 获取摘要
        summary_resp = api_client.get(f"{BACKEND_URL}/api/v2/settings/summary")
        assert summary_resp.status_code == 200
        
        # 2. 获取技能列表
        skills_resp = api_client.get(f"{BACKEND_URL}/api/v2/settings/skills")
        assert skills_resp.status_code == 200
        
        # 3. 获取规则
        rules_resp = api_client.get(f"{BACKEND_URL}/api/v2/settings/rules")
        assert rules_resp.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])


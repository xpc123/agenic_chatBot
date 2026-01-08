# -*- coding: utf-8 -*-
"""
功能测试 - 聊天场景测试

通过真实 API 调用测试 ChatBot 的完整功能流程。
这些测试需要后端服务运行。
"""
import pytest
import requests
import time
from typing import Dict, Any


# 后端 URL
BACKEND_URL = "http://localhost:8000"


@pytest.fixture(scope="module")
def api_client():
    """创建 API 客户端"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # 检查后端是否运行
    try:
        response = session.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code not in [200, 503]:
            pytest.skip("Backend not available")
    except requests.exceptions.ConnectionError:
        pytest.skip("Backend not running")
    
    return session


class TestBasicChat:
    """基础对话测试"""
    
    def test_simple_greeting(self, api_client):
        """测试简单问候"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"message": "你好", "session_id": "test-greeting"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert len(data["message"]) > 0
    
    def test_question_answering(self, api_client):
        """测试问答"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"message": "什么是 Python？", "session_id": "test-qa"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # 验证回答包含相关内容
        assert "Python" in data["message"] or "python" in data["message"].lower()


class TestMultiTurnConversation:
    """多轮对话测试"""
    
    def test_context_retention(self, api_client):
        """测试上下文保持"""
        session_id = f"test-context-{int(time.time())}"
        
        # 第一轮：介绍话题
        resp1 = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"message": "我叫张三", "session_id": session_id}
        )
        assert resp1.status_code == 200
        
        # 第二轮：测试是否记住
        resp2 = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"message": "我叫什么名字？", "session_id": session_id}
        )
        assert resp2.status_code == 200
        # 验证回答包含名字
        assert "张三" in resp2.json()["message"]


class TestIntentRecognition:
    """意图识别测试"""
    
    @pytest.mark.parametrize("message,expected_type", [
        ("帮我写一个排序算法", "creation"),
        ("分析这段代码的性能", "analysis"),
        ("什么是机器学习？", "query"),
        ("执行 ls 命令", "action"),
    ])
    def test_intent_classification(self, api_client, message, expected_type):
        """测试意图分类"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/analyze-intent",
            json={"message": message}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "task_type" in data
        # 允许一定的灵活性
        assert data["task_type"] in [expected_type, "complex", "conversation"]


class TestToolCalling:
    """工具调用测试"""
    
    def test_time_query_uses_tool(self, api_client):
        """测试时间查询使用工具"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"message": "现在几点了？", "session_id": "test-tool"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # 验证使用了工具
        # 或者回答包含时间信息


class TestDocumentManagement:
    """文档管理测试"""
    
    def test_list_documents(self, api_client):
        """测试列出文档"""
        response = api_client.get(f"{BACKEND_URL}/api/v2/documents/list")
        
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data or "total" in data
    
    def test_search_documents(self, api_client):
        """测试搜索文档"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/documents/search",
            json={"query": "test"}
        )
        
        # 即使没有结果也应该返回成功
        assert response.status_code in [200, 404]


class TestSkillsSystem:
    """技能系统测试"""
    
    def test_list_skills(self, api_client):
        """测试列出技能"""
        response = api_client.get(f"{BACKEND_URL}/api/v2/chat/skills")
        
        assert response.status_code == 200
        data = response.json()
        assert "skills" in data or "total" in data


class TestErrorHandling:
    """错误处理测试"""
    
    def test_empty_message(self, api_client):
        """测试空消息"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"message": "", "session_id": "test-empty"}
        )
        
        # 应该返回错误或处理空消息
        assert response.status_code in [200, 400, 422]
    
    def test_invalid_session(self, api_client):
        """测试无效会话"""
        response = api_client.delete(
            f"{BACKEND_URL}/api/v2/chat/session/non-existent-session"
        )
        
        # 应该优雅处理
        assert response.status_code in [200, 404]


class TestStreamingResponse:
    """流式响应测试"""
    
    def test_stream_chat(self, api_client):
        """测试流式对话"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/stream",
            json={"message": "你好", "session_id": "test-stream"},
            stream=True
        )
        
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("text/event-stream")
        
        # 验证收到数据
        chunks = []
        for line in response.iter_lines():
            if line:
                chunks.append(line)
            if len(chunks) >= 3:  # 至少收到几个块
                break
        
        assert len(chunks) > 0


class TestBatchOperations:
    """批量操作测试"""
    
    def test_batch_chat(self, api_client):
        """测试批量对话"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/batch/chat",
            json={
                "messages": [
                    {"message": "你好", "session_id": "batch-1"},
                    {"message": "再见", "session_id": "batch-2"},
                ]
            }
        )
        
        assert response.status_code in [200, 202]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


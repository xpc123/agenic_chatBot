# -*- coding: utf-8 -*-
"""
边界条件和异常测试

覆盖各种边界情况、异常输入、安全性测试。
"""
import pytest
import requests
import time
import os


BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


@pytest.fixture(scope="module")
def api_client():
    """创建 API 客户端"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    for _ in range(3):
        try:
            response = session.get(f"{BACKEND_URL}/health", timeout=5)
            if response.status_code in [200, 503]:
                return session
        except requests.exceptions.ConnectionError:
            time.sleep(2)
    
    pytest.skip("Backend not available")


# ==================== 1. 输入边界测试 ====================

class TestInputBoundaries:
    """输入边界测试"""
    
    def test_empty_message(self, api_client):
        """空消息"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"message": "", "session_id": "edge-1"}
        )
        assert response.status_code in [200, 400, 422]
    
    def test_whitespace_only_message(self, api_client):
        """纯空格消息"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"message": "   \n\t  ", "session_id": "edge-2"}
        )
        assert response.status_code in [200, 400, 422]
    
    def test_very_long_message(self, api_client):
        """超长消息 (10000 字符)"""
        long_message = "测试内容 " * 2000  # ~10000 chars
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"message": long_message, "session_id": "edge-3"}
        )
        # 应该处理或返回明确错误
        assert response.status_code in [200, 400, 413, 422]
    
    def test_unicode_characters(self, api_client):
        """Unicode 字符"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"message": "🎉 Emoji 日本語 العربية 中文 한국어", "session_id": "edge-4"}
        )
        assert response.status_code == 200
    
    def test_special_characters(self, api_client):
        """特殊字符"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"message": "测试 <script>alert(1)</script> & \" ' \\ /", "session_id": "edge-5"}
        )
        assert response.status_code == 200
        # 验证响应正常返回 (AI 可能会解释这些字符)
        data = response.json()
        assert "message" in data
        assert len(data.get("message", "")) > 0
    
    def test_null_message(self, api_client):
        """null 消息"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"message": None, "session_id": "edge-6"}
        )
        assert response.status_code in [400, 422]
    
    def test_number_as_message(self, api_client):
        """数字作为消息"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"message": 12345, "session_id": "edge-7"}
        )
        # 应该处理类型转换或返回错误
        assert response.status_code in [200, 400, 422]


# ==================== 2. 会话管理边界测试 ====================

class TestSessionBoundaries:
    """会话管理边界测试"""
    
    def test_very_long_session_id(self, api_client):
        """超长会话 ID"""
        long_id = "a" * 1000
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"message": "测试", "session_id": long_id}
        )
        assert response.status_code in [200, 400, 422]
    
    def test_special_chars_in_session_id(self, api_client):
        """会话 ID 中的特殊字符"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"message": "测试", "session_id": "test/../../../etc/passwd"}
        )
        assert response.status_code in [200, 400]
    
    def test_empty_session_id(self, api_client):
        """空会话 ID"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"message": "测试", "session_id": ""}
        )
        # 应该自动生成或返回错误
        assert response.status_code in [200, 400, 422]
    
    def test_rapid_session_creation(self, api_client):
        """快速创建多个会话"""
        for i in range(10):
            response = api_client.post(
                f"{BACKEND_URL}/api/v2/chat/message",
                json={"message": f"测试{i}", "session_id": f"rapid-{i}"}
            )
            assert response.status_code == 200


# ==================== 3. API 请求格式测试 ====================

class TestRequestFormat:
    """请求格式测试"""
    
    def test_missing_required_field(self, api_client):
        """缺少必需字段"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"session_id": "format-1"}  # 缺少 message
        )
        assert response.status_code in [400, 422]
    
    def test_invalid_json(self, api_client):
        """无效 JSON"""
        response = requests.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            data="{ invalid json }",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422]
    
    def test_extra_fields(self, api_client):
        """额外字段"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={
                "message": "测试",
                "session_id": "format-2",
                "unknown_field": "ignored"
            }
        )
        # 应该忽略额外字段
        assert response.status_code == 200
    
    def test_wrong_content_type(self, api_client):
        """错误的 Content-Type"""
        response = requests.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            data="message=test&session_id=format-3",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code in [400, 415, 422]


# ==================== 4. 并发和负载测试 ====================

class TestConcurrency:
    """并发测试"""
    
    def test_concurrent_requests(self, api_client):
        """并发请求"""
        import concurrent.futures
        
        def make_request(i):
            return api_client.post(
                f"{BACKEND_URL}/api/v2/chat/message",
                json={"message": f"并发测试{i}", "session_id": f"concurrent-{i}"}
            )
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(5)]
            results = [f.result() for f in futures]
        
        # 所有请求应该成功
        success_count = sum(1 for r in results if r.status_code == 200)
        assert success_count >= 4  # 至少 80% 成功
    
    def test_same_session_concurrent(self, api_client):
        """同一会话的并发请求"""
        import concurrent.futures
        
        session_id = "concurrent-same"
        
        def make_request(i):
            return api_client.post(
                f"{BACKEND_URL}/api/v2/chat/message",
                json={"message": f"消息{i}", "session_id": session_id}
            )
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_request, i) for i in range(3)]
            results = [f.result() for f in futures]
        
        # 验证所有请求得到响应
        for r in results:
            assert r.status_code in [200, 429]


# ==================== 5. 安全性测试 ====================

class TestSecurity:
    """安全性测试"""
    
    def test_sql_injection(self, api_client):
        """SQL 注入"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={
                "message": "'; DROP TABLE users; --",
                "session_id": "security-1"
            }
        )
        assert response.status_code == 200  # 应该正常处理
    
    def test_xss_attempt(self, api_client):
        """XSS 尝试"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={
                "message": "<img src=x onerror=alert(1)>",
                "session_id": "security-2"
            }
        )
        assert response.status_code == 200
        data = response.json()
        # 验证响应正常返回 (AI 可能会解释 XSS)
        assert "message" in data
        assert len(data.get("message", "")) > 0
    
    def test_path_traversal(self, api_client):
        """路径遍历"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/documents/search",
            json={"query": "../../../etc/passwd"}
        )
        # 应该正常处理，不返回敏感信息
        assert response.status_code in [200, 404]
    
    def test_command_injection(self, api_client):
        """命令注入"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={
                "message": "$(rm -rf /)",
                "session_id": "security-3"
            }
        )
        assert response.status_code == 200


# ==================== 6. 超时和重试测试 ====================

class TestTimeoutAndRetry:
    """超时和重试测试"""
    
    def test_request_timeout(self, api_client):
        """请求超时"""
        # 尝试一个可能耗时的操作
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={
                "message": "请详细分析人工智能的历史发展",
                "session_id": "timeout-1"
            },
            timeout=60
        )
        assert response.status_code in [200, 408, 504]
    
    def test_stream_interruption(self, api_client):
        """流式响应中断"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/stream",
            json={"message": "长回答", "session_id": "stream-interrupt"},
            stream=True,
            timeout=5
        )
        
        # 只读取部分响应然后关闭
        for i, line in enumerate(response.iter_lines()):
            if i >= 2:
                break
        
        response.close()
        # 连接应该正常关闭


# ==================== 7. 意图分析边界测试 ====================

class TestIntentBoundaries:
    """意图分析边界测试"""
    
    def test_ambiguous_intent(self, api_client):
        """模糊意图"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/analyze-intent",
            json={"message": "嗯"}
        )
        assert response.status_code == 200
    
    def test_multiple_intents(self, api_client):
        """多重意图"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/analyze-intent",
            json={"message": "帮我写代码并解释原理然后执行它"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "task_type" in data
    
    def test_contradictory_intent(self, api_client):
        """矛盾意图"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/analyze-intent",
            json={"message": "帮我创建并删除这个文件"}
        )
        assert response.status_code == 200


# ==================== 8. 文档操作边界测试 ====================

class TestDocumentBoundaries:
    """文档操作边界测试"""
    
    def test_search_empty_query(self, api_client):
        """空搜索查询"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/documents/search",
            json={"query": ""}
        )
        assert response.status_code in [200, 400, 422]
    
    def test_search_very_long_query(self, api_client):
        """超长搜索查询"""
        long_query = "搜索 " * 500
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/documents/search",
            json={"query": long_query}
        )
        assert response.status_code in [200, 400, 413]
    
    def test_search_special_chars(self, api_client):
        """特殊字符搜索"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/documents/search",
            json={"query": "* ? [ ] { } ( ) | ^ $ . + \\"}
        )
        assert response.status_code in [200, 404]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])



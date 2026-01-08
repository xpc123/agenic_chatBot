# -*- coding: utf-8 -*-
"""
SDK 客户端测试

测试简化后的 SDK (agentic_sdk.ChatBot) 功能：
- 连接和初始化
- 对话 API
- 流式响应
- 文档 API
- 设置 API
- 错误处理
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestChatBotInitialization:
    """测试 ChatBot 初始化"""
    
    def test_init_with_base_url(self):
        """测试使用 base_url 初始化"""
        from agentic_sdk import ChatBot
        
        bot = ChatBot(base_url="http://localhost:8000")
        
        assert bot.base_url == "http://localhost:8000"
        assert bot.api_key is None
        assert bot.timeout == 60
    
    def test_init_with_api_key(self):
        """测试使用 API Key 初始化"""
        from agentic_sdk import ChatBot
        
        bot = ChatBot(
            base_url="http://localhost:8000",
            api_key="test-api-key",
        )
        
        assert bot.api_key == "test-api-key"
    
    def test_init_without_base_url_raises_error(self):
        """测试没有 base_url 抛出错误"""
        from agentic_sdk import ChatBot
        
        with pytest.raises(ValueError, match="base_url is required"):
            ChatBot(base_url="")
    
    def test_init_strips_trailing_slash(self):
        """测试移除尾部斜杠"""
        from agentic_sdk import ChatBot
        
        bot = ChatBot(base_url="http://localhost:8000/")
        
        assert bot.base_url == "http://localhost:8000"
    
    def test_context_manager(self):
        """测试上下文管理器"""
        from agentic_sdk import ChatBot
        
        with ChatBot(base_url="http://localhost:8000") as bot:
            assert bot.base_url == "http://localhost:8000"
    
    def test_repr(self):
        """测试字符串表示"""
        from agentic_sdk import ChatBot
        
        bot = ChatBot(base_url="http://localhost:8000")
        
        assert "ChatBot" in repr(bot)
        assert "localhost:8000" in repr(bot)


class TestChatBotHeaders:
    """测试请求头生成"""
    
    def test_headers_without_api_key(self):
        """测试没有 API Key 的请求头"""
        from agentic_sdk import ChatBot
        
        bot = ChatBot(base_url="http://localhost:8000")
        headers = bot._get_headers()
        
        assert headers["Content-Type"] == "application/json"
        assert "User-Agent" in headers
        assert "X-API-Key" not in headers
    
    def test_headers_with_api_key(self):
        """测试有 API Key 的请求头"""
        from agentic_sdk import ChatBot
        
        bot = ChatBot(base_url="http://localhost:8000", api_key="test-key")
        headers = bot._get_headers()
        
        assert headers["X-API-Key"] == "test-key"


class TestChatAPI:
    """测试对话 API"""
    
    @pytest.fixture
    def mock_bot(self):
        """创建 Mock ChatBot"""
        from agentic_sdk import ChatBot
        
        bot = ChatBot(base_url="http://localhost:8000")
        return bot
    
    def test_chat_success(self, mock_bot):
        """测试成功对话"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": "你好！有什么可以帮助你的？",
            "session_id": "test-session",
            "used_tools": [],
            "citations": [],
            "duration_ms": 100,
        }
        
        with patch.object(mock_bot._session, 'request', return_value=mock_response):
            response = mock_bot.chat("你好")
        
        assert response.text == "你好！有什么可以帮助你的？"
        assert response.session_id == "test-session"
    
    def test_chat_with_session_id(self, mock_bot):
        """测试带 session_id 的对话"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": "继续我们的对话...",
            "session_id": "existing-session",
            "used_tools": [],
            "citations": [],
        }
        
        with patch.object(mock_bot._session, 'request', return_value=mock_response):
            response = mock_bot.chat("继续", session_id="existing-session")
        
        assert response.session_id == "existing-session"
    
    def test_chat_with_rag_sources(self, mock_bot):
        """测试返回 RAG 来源"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": "根据文档...",
            "session_id": "test",
            "used_tools": [],
            "citations": [
                {"source": "doc1.pdf", "content": "相关内容"},
            ],
        }
        
        with patch.object(mock_bot._session, 'request', return_value=mock_response):
            response = mock_bot.chat("查询文档")
        
        assert len(response.sources) == 1
        assert response.sources[0]["source"] == "doc1.pdf"
    
    def test_chat_with_tool_calls(self, mock_bot):
        """测试返回工具调用"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": "已执行搜索...",
            "session_id": "test",
            "used_tools": ["search", "read_file"],
            "citations": [],
        }
        
        with patch.object(mock_bot._session, 'request', return_value=mock_response):
            response = mock_bot.chat("搜索代码")
        
        assert "search" in response.used_tools
        assert "read_file" in response.used_tools


class TestStreamingAPI:
    """测试流式响应 API"""
    
    @pytest.fixture
    def mock_bot(self):
        from agentic_sdk import ChatBot
        return ChatBot(base_url="http://localhost:8000")
    
    def test_chat_stream(self, mock_bot):
        """测试流式对话"""
        # 模拟 SSE 响应
        def mock_iter_lines():
            yield b'data: {"type": "text", "content": "Hello"}'
            yield b'data: {"type": "text", "content": " World"}'
            yield b'data: {"type": "complete", "content": ""}'
            yield b'data: [DONE]'
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines = mock_iter_lines
        
        with patch.object(mock_bot._session, 'request', return_value=mock_response):
            chunks = list(mock_bot.chat_stream("你好"))
        
        assert len(chunks) == 3
        assert chunks[0].type == "text"
        assert chunks[0].content == "Hello"
        assert chunks[1].content == " World"
        assert chunks[2].type == "complete"
    
    def test_chat_stream_with_tool_call(self, mock_bot):
        """测试流式响应中的工具调用"""
        def mock_iter_lines():
            yield b'data: {"type": "tool_call", "content": "search", "metadata": {"query": "test"}}'
            yield b'data: {"type": "tool_result", "content": "Found 3 results"}'
            yield b'data: {"type": "text", "content": "Based on search..."}'
            yield b'data: [DONE]'
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines = mock_iter_lines
        
        with patch.object(mock_bot._session, 'request', return_value=mock_response):
            chunks = list(mock_bot.chat_stream("搜索"))
        
        assert chunks[0].type == "tool_call"


class TestIntentAPI:
    """测试意图分析 API"""
    
    @pytest.fixture
    def mock_bot(self):
        from agentic_sdk import ChatBot
        return ChatBot(base_url="http://localhost:8000")
    
    def test_analyze_intent(self, mock_bot):
        """测试意图分析"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "surface_intent": "代码生成",
            "deep_intent": "创建 Python 函数",
            "task_type": "code_generation",
            "complexity": "medium",
            "is_multi_step": False,
            "suggested_tools": ["code_search", "write_file"],
            "confidence": 0.95,
        }
        
        with patch.object(mock_bot._session, 'request', return_value=mock_response):
            intent = mock_bot.analyze_intent("帮我写一个排序函数")
        
        assert intent.task_type == "code_generation"
        assert intent.confidence == 0.95
        assert "code_search" in intent.suggested_tools


class TestDocumentsAPI:
    """测试文档 API"""
    
    @pytest.fixture
    def mock_bot(self):
        from agentic_sdk import ChatBot
        return ChatBot(base_url="http://localhost:8000")
    
    def test_list_documents(self, mock_bot):
        """测试列出文档"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "documents": [
                {"id": "doc1", "name": "test.pdf"},
                {"id": "doc2", "name": "guide.md"},
            ],
            "total": 2,
            "page": 1,
        }
        
        with patch.object(mock_bot._session, 'request', return_value=mock_response):
            result = mock_bot.list_documents()
        
        assert result["total"] == 2
        assert len(result["documents"]) == 2
    
    def test_search_documents(self, mock_bot):
        """测试搜索文档"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"source": "doc1.pdf", "content": "相关内容", "score": 0.9},
            ],
        }
        
        with patch.object(mock_bot._session, 'request', return_value=mock_response):
            result = mock_bot.search_documents("关键词", top_k=5)
        
        assert len(result["results"]) == 1
        assert result["results"][0]["score"] == 0.9
    
    def test_delete_document(self, mock_bot):
        """测试删除文档"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Document deleted"}
        
        with patch.object(mock_bot._session, 'request', return_value=mock_response):
            result = mock_bot.delete_document("doc-123")
        
        assert result is True


class TestSettingsAPI:
    """测试设置 API"""
    
    @pytest.fixture
    def mock_bot(self):
        from agentic_sdk import ChatBot
        return ChatBot(base_url="http://localhost:8000")
    
    def test_list_skills(self, mock_bot):
        """测试列出技能"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "skills": [
                {"id": "code_assistant", "name": "代码助手", "enabled": True},
                {"id": "writing_assistant", "name": "写作助手", "enabled": False},
            ],
        }
        
        with patch.object(mock_bot._session, 'request', return_value=mock_response):
            skills = mock_bot.list_skills()
        
        assert len(skills) == 2
        assert skills[0]["id"] == "code_assistant"
    
    def test_toggle_skill(self, mock_bot):
        """测试切换技能"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        
        with patch.object(mock_bot._session, 'request', return_value=mock_response):
            result = mock_bot.toggle_skill("code_assistant", enabled=False)
        
        assert result is True
    
    def test_get_rules(self, mock_bot):
        """测试获取规则"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "user_rules": ["规则1"],
            "project_rules": ["规则2"],
        }
        
        with patch.object(mock_bot._session, 'request', return_value=mock_response):
            rules = mock_bot.get_rules()
        
        assert "user_rules" in rules
        assert "project_rules" in rules
    
    def test_add_rule(self, mock_bot):
        """测试添加规则"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        
        with patch.object(mock_bot._session, 'request', return_value=mock_response):
            result = mock_bot.add_rule("始终使用中文回答", rule_type="user")
        
        assert result is True


class TestBatchAPI:
    """测试批量 API"""
    
    @pytest.fixture
    def mock_bot(self):
        from agentic_sdk import ChatBot
        return ChatBot(base_url="http://localhost:8000")
    
    def test_chat_batch(self, mock_bot):
        """测试批量对话"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"success": True, "message": "回复1", "session_id": "s1"},
                {"success": True, "message": "回复2", "session_id": "s2"},
                {"success": False, "error": "处理失败"},
            ],
        }
        
        with patch.object(mock_bot._session, 'request', return_value=mock_response):
            responses = mock_bot.chat_batch(["问题1", "问题2", "问题3"])
        
        assert len(responses) == 3
        assert responses[0].text == "回复1"
        assert responses[1].text == "回复2"
        assert "Error" in responses[2].text


class TestErrorHandling:
    """测试错误处理"""
    
    @pytest.fixture
    def mock_bot(self):
        from agentic_sdk import ChatBot
        return ChatBot(base_url="http://localhost:8000")
    
    def test_connection_error(self, mock_bot):
        """测试连接错误"""
        import requests
        from agentic_sdk import ConnectionError
        
        with patch.object(mock_bot._session, 'request', 
                         side_effect=requests.ConnectionError("Connection refused")):
            with pytest.raises(ConnectionError, match="Cannot connect"):
                mock_bot.chat("你好")
    
    def test_authentication_error(self, mock_bot):
        """测试认证错误"""
        from agentic_sdk import AuthenticationError
        
        mock_response = Mock()
        mock_response.status_code = 401
        
        with patch.object(mock_bot._session, 'request', return_value=mock_response):
            with pytest.raises(AuthenticationError, match="Authentication failed"):
                mock_bot.chat("你好")
    
    def test_api_error(self, mock_bot):
        """测试 API 错误"""
        from agentic_sdk import APIError
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.side_effect = Exception("No JSON")
        
        with patch.object(mock_bot._session, 'request', return_value=mock_response):
            with pytest.raises(APIError, match="API error"):
                mock_bot.chat("你好")
    
    def test_timeout_error(self, mock_bot):
        """测试超时错误"""
        import requests
        from agentic_sdk import ConnectionError
        
        with patch.object(mock_bot._session, 'request', 
                         side_effect=requests.Timeout("Request timeout")):
            with pytest.raises(ConnectionError, match="timeout"):
                mock_bot.chat("你好")
    
    def test_invalid_feedback(self, mock_bot):
        """测试无效反馈值"""
        with pytest.raises(ValueError, match="must be 'positive' or 'negative'"):
            mock_bot.submit_feedback("session-123", feedback="invalid")


class TestTypes:
    """测试类型定义"""
    
    def test_chat_response_properties(self):
        """测试 ChatResponse 属性"""
        from agentic_sdk.types import ChatResponse, ToolCall
        
        response = ChatResponse(
            text="Hello",
            session_id="test",
            used_tools=["search"],
            sources=[{"source": "doc.pdf"}],
        )
        
        assert response.has_tool_calls is True
        assert response.has_sources is True
    
    def test_chat_chunk_properties(self):
        """测试 ChatChunk 属性"""
        from agentic_sdk.types import ChatChunk
        
        chunk = ChatChunk(type="text", content="Hello")
        assert chunk.is_text is True
        assert chunk.is_complete is False
        assert chunk.is_error is False
        
        complete_chunk = ChatChunk(type="complete", content="")
        assert complete_chunk.is_complete is True
    
    def test_intent_result(self):
        """测试 IntentResult"""
        from agentic_sdk.types import IntentResult
        
        intent = IntentResult(
            surface_intent="代码生成",
            deep_intent="创建函数",
            task_type="code_generation",
            complexity="medium",
            is_multi_step=True,
            suggested_tools=["write_file"],
            confidence=0.9,
        )
        
        assert intent.task_type == "code_generation"
        assert intent.is_multi_step is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


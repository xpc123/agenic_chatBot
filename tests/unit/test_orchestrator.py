# -*- coding: utf-8 -*-
"""
编排器测试

测试 CursorStyleOrchestrator 的功能：
- ReAct 循环
- 多轮对话
- 工具编排
- 上下文管理
- 复杂推理任务
"""
import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


@pytest.fixture
def mock_llm_client():
    """Mock LLM 客户端"""
    mock = AsyncMock()
    mock.chat_completion = AsyncMock(return_value="这是 LLM 的回复")
    mock.streaming_chat = AsyncMock()
    return mock


@pytest.fixture
def simple_tools():
    """简单测试工具"""
    from langchain_core.tools import tool
    
    @tool
    def calculator(expression: str) -> str:
        """计算数学表达式"""
        try:
            result = eval(expression)
            return f"计算结果: {result}"
        except Exception as e:
            return f"计算错误: {e}"
    
    @tool
    def get_weather(city: str) -> str:
        """获取天气信息"""
        return f"{city}的天气: 晴，25°C"
    
    return [calculator, get_weather]


class TestOrchestratorInitialization:
    """测试编排器初始化"""
    
    def test_create_orchestrator(self, mock_llm_client, simple_tools):
        """测试创建编排器"""
        from app.core.cursor_style_orchestrator import CursorStyleOrchestrator
        
        orchestrator = CursorStyleOrchestrator(
            llm_client=mock_llm_client,
            tools=simple_tools,
            enable_rag=False,
            enable_skills=False,
            enable_memory=False,
        )
        
        assert orchestrator is not None
        assert len(orchestrator.tools) >= 2
    
    def test_orchestrator_default_config(self, mock_llm_client):
        """测试默认配置"""
        from app.core.cursor_style_orchestrator import CursorStyleOrchestrator
        
        orchestrator = CursorStyleOrchestrator(
            llm_client=mock_llm_client,
            tools=[],
        )
        
        # 检查默认配置
        assert orchestrator.max_iterations > 0
        assert orchestrator.sessions == {}


class TestReActLoop:
    """测试 ReAct 循环"""
    
    @pytest.fixture
    def orchestrator(self, mock_llm_client, simple_tools):
        from app.core.cursor_style_orchestrator import CursorStyleOrchestrator
        
        return CursorStyleOrchestrator(
            llm_client=mock_llm_client,
            tools=simple_tools,
            enable_rag=False,
            enable_skills=False,
            enable_memory=False,
            enable_preferences=False,
        )
    
    @pytest.mark.asyncio
    async def test_simple_chat(self, orchestrator, mock_llm_client):
        """测试简单对话"""
        mock_llm_client.chat_completion.return_value = "你好！有什么可以帮助你的？"
        
        result = await orchestrator.chat("你好", session_id="test")
        
        assert result["message"] is not None
        assert result["session_id"] == "test"
    
    @pytest.mark.asyncio
    async def test_tool_execution(self, orchestrator, mock_llm_client):
        """测试工具执行"""
        # 模拟 LLM 返回工具调用
        mock_llm_client.chat_completion.side_effect = [
            Mock(
                content="",
                tool_calls=[Mock(
                    function=Mock(
                        name="calculator",
                        arguments='{"expression": "2 + 2"}'
                    )
                )]
            ),
            "计算结果是 4",
        ]
        
        result = await orchestrator.chat("计算 2 + 2", session_id="test")
        
        # 应该执行工具并返回结果
        assert result["message"] is not None
    
    @pytest.mark.asyncio
    async def test_max_iterations_limit(self, orchestrator, mock_llm_client):
        """测试最大迭代限制"""
        # 模拟持续的工具调用
        mock_llm_client.chat_completion.return_value = Mock(
            content="",
            tool_calls=[Mock(
                function=Mock(
                    name="calculator",
                    arguments='{"expression": "1 + 1"}'
                )
            )]
        )
        
        orchestrator.max_iterations = 3
        
        result = await orchestrator.chat("无限循环测试", session_id="test")
        
        # 应该在达到最大迭代后停止
        assert result is not None


class TestMultiTurnConversation:
    """测试多轮对话"""
    
    @pytest.fixture
    def orchestrator(self, mock_llm_client, simple_tools):
        from app.core.cursor_style_orchestrator import CursorStyleOrchestrator
        
        return CursorStyleOrchestrator(
            llm_client=mock_llm_client,
            tools=simple_tools,
            enable_rag=False,
            enable_skills=False,
            enable_memory=False,
            enable_preferences=False,
        )
    
    @pytest.mark.asyncio
    async def test_context_preservation(self, orchestrator, mock_llm_client):
        """测试上下文保留"""
        mock_llm_client.chat_completion.return_value = "回复1"
        await orchestrator.chat("问题1", session_id="multi-turn")
        
        mock_llm_client.chat_completion.return_value = "回复2"
        await orchestrator.chat("问题2", session_id="multi-turn")
        
        # 检查历史记录
        session = orchestrator.sessions.get("multi-turn")
        assert session is not None
        assert len(session.get("history", [])) >= 4  # 2 user + 2 assistant
    
    @pytest.mark.asyncio
    async def test_session_isolation(self, orchestrator, mock_llm_client):
        """测试会话隔离"""
        mock_llm_client.chat_completion.return_value = "回复"
        
        await orchestrator.chat("问题", session_id="session-1")
        await orchestrator.chat("问题", session_id="session-2")
        
        # 两个会话应该独立
        assert "session-1" in orchestrator.sessions
        assert "session-2" in orchestrator.sessions
        assert orchestrator.sessions["session-1"] != orchestrator.sessions["session-2"]
    
    @pytest.mark.asyncio
    async def test_clear_session(self, orchestrator, mock_llm_client):
        """测试清除会话"""
        mock_llm_client.chat_completion.return_value = "回复"
        
        await orchestrator.chat("问题", session_id="to-clear")
        assert "to-clear" in orchestrator.sessions
        
        orchestrator.clear_session("to-clear")
        assert "to-clear" not in orchestrator.sessions


class TestComplexReasoning:
    """测试复杂推理任务"""
    
    @pytest.fixture
    def orchestrator(self, mock_llm_client, simple_tools):
        from app.core.cursor_style_orchestrator import CursorStyleOrchestrator
        
        return CursorStyleOrchestrator(
            llm_client=mock_llm_client,
            tools=simple_tools,
            enable_rag=False,
            enable_skills=False,
            enable_memory=False,
            enable_preferences=False,
        )
    
    @pytest.mark.asyncio
    async def test_multi_step_task(self, orchestrator, mock_llm_client):
        """测试多步骤任务"""
        # 模拟多步骤推理
        mock_llm_client.chat_completion.side_effect = [
            Mock(
                content="让我先计算第一步...",
                tool_calls=[Mock(
                    function=Mock(
                        name="calculator",
                        arguments='{"expression": "10 * 5"}'
                    )
                )]
            ),
            Mock(
                content="现在计算第二步...",
                tool_calls=[Mock(
                    function=Mock(
                        name="calculator",
                        arguments='{"expression": "50 + 25"}'
                    )
                )]
            ),
            "最终结果是 75",
        ]
        
        result = await orchestrator.chat(
            "计算 10 * 5 然后加 25",
            session_id="multi-step"
        )
        
        assert result["message"] is not None
    
    @pytest.mark.asyncio
    async def test_error_recovery(self, orchestrator, mock_llm_client):
        """测试错误恢复"""
        mock_llm_client.chat_completion.side_effect = [
            Mock(
                content="",
                tool_calls=[Mock(
                    function=Mock(
                        name="calculator",
                        arguments='{"expression": "invalid"}'  # 会导致错误
                    )
                )]
            ),
            "抱歉，计算出错了。让我尝试其他方式...",
        ]
        
        result = await orchestrator.chat(
            "计算 invalid",
            session_id="error-test"
        )
        
        # 应该能处理错误并继续
        assert result["message"] is not None


class TestStreamingResponse:
    """测试流式响应"""
    
    @pytest.fixture
    def orchestrator(self, mock_llm_client, simple_tools):
        from app.core.cursor_style_orchestrator import CursorStyleOrchestrator
        
        return CursorStyleOrchestrator(
            llm_client=mock_llm_client,
            tools=simple_tools,
            enable_rag=False,
            enable_skills=False,
            enable_memory=False,
            enable_preferences=False,
        )
    
    @pytest.mark.asyncio
    async def test_streaming_chat(self, orchestrator, mock_llm_client):
        """测试流式对话"""
        async def mock_stream():
            yield Mock(content="Hello", tool_calls=None)
            yield Mock(content=" World", tool_calls=None)
            yield Mock(content="!", tool_calls=None)
        
        mock_llm_client.streaming_chat = mock_stream
        
        chunks = []
        async for chunk in orchestrator.chat_stream("你好", session_id="stream-test"):
            chunks.append(chunk)
        
        # 应该收到多个 chunk
        assert len(chunks) > 0


class TestSessionCompaction:
    """测试会话压缩"""
    
    @pytest.fixture
    def orchestrator(self, mock_llm_client, simple_tools):
        from app.core.cursor_style_orchestrator import CursorStyleOrchestrator
        
        return CursorStyleOrchestrator(
            llm_client=mock_llm_client,
            tools=simple_tools,
            enable_rag=False,
            enable_skills=False,
            enable_memory=False,
            enable_preferences=False,
        )
    
    @pytest.mark.asyncio
    async def test_compact_session(self, orchestrator):
        """测试会话压缩"""
        # 创建长会话
        session_id = "compact-test"
        orchestrator.sessions[session_id] = {
            "history": [
                {"role": "user", "content": f"消息 {i}" * 100}
                for i in range(30)
            ],
            "tool_results": [],
        }
        
        # 执行压缩
        result = await orchestrator.compact_session(session_id, force=True)
        
        # 应该成功压缩
        assert result is not None
        assert result.original_messages > result.compacted_messages


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


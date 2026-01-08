# -*- coding: utf-8 -*-
"""
Pytest 配置和共享 Fixtures

提供测试所需的通用组件和配置
"""
import pytest
import asyncio
import sys
from pathlib import Path
from typing import Generator, Optional
from unittest.mock import Mock, AsyncMock, patch

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))


# ============================================================================
# Pytest 配置
# ============================================================================

def pytest_configure(config):
    """Pytest 配置钩子"""
    config.addinivalue_line(
        "markers", "slow: 标记慢速测试"
    )
    config.addinivalue_line(
        "markers", "integration: 标记集成测试"
    )
    config.addinivalue_line(
        "markers", "e2e: 标记端到端测试"
    )
    config.addinivalue_line(
        "markers", "regression: 标记回归测试"
    )
    config.addinivalue_line(
        "markers", "benchmark: 标记性能基准测试"
    )
    config.addinivalue_line(
        "markers", "unit: 标记单元测试"
    )


# ============================================================================
# 基础 Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def project_root() -> Path:
    """项目根目录"""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def backend_path() -> Path:
    """Backend 目录"""
    return PROJECT_ROOT / "backend"


# ============================================================================
# ChatBot Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def chatbot():
    """
    ChatBot 实例 (真实)
    
    用于集成测试和 E2E 测试
    需要后端服务运行在 localhost:8000
    """
    from agentic_sdk import ChatBot
    try:
        bot = ChatBot(base_url="http://localhost:8000")
        # 测试连接
        bot.health_check()
        yield bot
        bot.close()
    except Exception:
        pytest.skip("Backend service not running")


@pytest.fixture
def mock_chatbot():
    """
    Mock ChatBot
    
    用于单元测试，不调用真实 LLM
    """
    mock = Mock()
    mock.chat_stream = Mock(return_value=iter([
        Mock(type="text", content="这是 Mock 响应"),
        Mock(type="complete", content="", metadata={"duration_ms": 100}),
    ]))
    mock.chat = AsyncMock(return_value=Mock(
        content="这是 Mock 响应",
        tool_calls=[],
    ))
    return mock


# ============================================================================
# LLM Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_client():
    """Mock LLM Client"""
    mock = AsyncMock()
    mock.chat_completion = AsyncMock(return_value="这是 LLM 的 Mock 响应")
    mock.streaming_chat = AsyncMock()
    return mock


@pytest.fixture(scope="module")
def real_llm_client():
    """真实 LLM Client（谨慎使用，会消耗配额）"""
    from app.llm import get_llm_client
    return get_llm_client()


# ============================================================================
# 组件 Fixtures
# ============================================================================

@pytest.fixture
def intent_recognizer(mock_llm_client):
    """意图识别器"""
    from app.core.intent_recognizer import IntentRecognizer
    return IntentRecognizer(llm=mock_llm_client)


@pytest.fixture
def context_manager():
    """上下文管理器"""
    from app.core.context_manager import ContextManager
    return ContextManager(max_tokens=8000)


@pytest.fixture
def tool_orchestrator():
    """工具编排器"""
    from app.core.tool_orchestrator import ToolOrchestrator
    return ToolOrchestrator()


@pytest.fixture
def memory_manager():
    """记忆管理器"""
    from app.core.memory import MemoryManager
    return MemoryManager()


# ============================================================================
# 测试数据 Fixtures
# ============================================================================

@pytest.fixture
def sample_conversation():
    """示例对话历史"""
    return [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮助你的吗？"},
        {"role": "user", "content": "帮我看看 /tmp 目录"},
    ]


@pytest.fixture
def sample_file_content():
    """示例文件内容"""
    return """# Sample Python File
def hello():
    print("Hello, World!")

if __name__ == "__main__":
    hello()
"""


@pytest.fixture
def sample_directory_structure():
    """示例目录结构"""
    return {
        "dirs": ["src", "tests", "docs"],
        "files": ["README.md", "setup.py", "requirements.txt"],
    }


# ============================================================================
# 工具 Fixtures
# ============================================================================

@pytest.fixture
def temp_test_dir(tmp_path):
    """临时测试目录"""
    # 创建测试文件
    test_file = tmp_path / "test.txt"
    test_file.write_text("This is a test file.")
    
    test_py = tmp_path / "test.py"
    test_py.write_text("print('hello')")
    
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    (sub_dir / "nested.txt").write_text("Nested file")
    
    return tmp_path


# ============================================================================
# 性能测试 Fixtures
# ============================================================================

@pytest.fixture
def performance_tracker():
    """性能追踪器"""
    import time
    
    class PerformanceTracker:
        def __init__(self):
            self.measurements = []
            self._start = None
            
        def start(self):
            self._start = time.time()
            
        def stop(self) -> float:
            elapsed = (time.time() - self._start) * 1000
            self.measurements.append(elapsed)
            return elapsed
            
        @property
        def avg_ms(self) -> float:
            return sum(self.measurements) / len(self.measurements) if self.measurements else 0
            
        @property
        def p50_ms(self) -> float:
            if not self.measurements:
                return 0
            sorted_m = sorted(self.measurements)
            return sorted_m[len(sorted_m) // 2]
            
        @property
        def p95_ms(self) -> float:
            if not self.measurements:
                return 0
            sorted_m = sorted(self.measurements)
            idx = int(len(sorted_m) * 0.95)
            return sorted_m[min(idx, len(sorted_m) - 1)]
            
    return PerformanceTracker()


# ============================================================================
# 回归测试 Fixtures
# ============================================================================

@pytest.fixture
def golden_cases():
    """加载黄金用例"""
    import json
    golden_file = Path(__file__).parent / "regression" / "golden_cases.json"
    if golden_file.exists():
        with open(golden_file) as f:
            return json.load(f)
    return []


@pytest.fixture
def regression_session_id():
    """回归测试 Session ID"""
    import uuid
    return f"regression-{uuid.uuid4().hex[:8]}"


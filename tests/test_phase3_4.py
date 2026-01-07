# -*- coding: utf-8 -*-
"""
Phase 3 & 4 功能测试

测试内容：
- Phase 3: 对话压缩 (SessionCompactor)
- Phase 4: 增强工具 (Enhanced Tools)
"""
import pytest
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSessionCompactor:
    """Phase 3: 会话压缩器测试"""
    
    @pytest.fixture
    def compactor(self):
        from backend.app.core.session_compactor import SessionCompactor, CompactionConfig
        config = CompactionConfig(
            auto_compact_threshold=500,  # 较低阈值便于测试
            target_tokens=200,
            preserve_recent=2,
            prune_tool_outputs=True,
            max_tool_output_length=100,
            generate_summary=False,  # 测试时不使用 LLM
        )
        return SessionCompactor(config=config)
    
    @pytest.fixture
    def sample_messages(self):
        from backend.app.models.chat import ChatMessage, MessageRole
        messages = []
        
        # 创建 10 条消息
        for i in range(10):
            if i % 2 == 0:
                role = MessageRole.USER
                content = f"这是用户的第 {i // 2 + 1} 条消息，包含一些测试内容。"
            else:
                role = MessageRole.ASSISTANT
                content = f"这是助手的回复 {i // 2 + 1}，包含详细的解释和说明。" * 5
            
            messages.append(ChatMessage(
                role=role,
                content=content,
                timestamp=datetime.now(),
                metadata={"index": i},
            ))
        
        return messages
    
    def test_count_tokens(self, compactor):
        """测试 Token 计数"""
        text = "Hello, this is a test message."
        tokens = compactor.count_tokens(text)
        assert tokens > 0
        assert isinstance(tokens, int)
    
    def test_count_messages_tokens(self, compactor, sample_messages):
        """测试消息列表 Token 计数"""
        tokens = compactor.count_messages_tokens(sample_messages)
        assert tokens > 0
    
    def test_should_compact(self, compactor, sample_messages):
        """测试压缩判断"""
        # 少量消息不需要压缩
        from backend.app.models.chat import ChatMessage, MessageRole
        small_messages = [
            ChatMessage(role=MessageRole.USER, content="Hi"),
            ChatMessage(role=MessageRole.ASSISTANT, content="Hello"),
        ]
        assert not compactor.should_compact(small_messages)
        
        # 大量消息需要压缩（阈值设为 500）
        # 创建足够多的消息
        large_messages = []
        for i in range(20):
            large_messages.append(ChatMessage(
                role=MessageRole.USER,
                content="这是一条很长的测试消息，用于测试压缩功能。" * 10,
            ))
        
        assert compactor.should_compact(large_messages)
    
    @pytest.mark.asyncio
    async def test_compact(self, compactor):
        """测试压缩功能"""
        from backend.app.models.chat import ChatMessage, MessageRole
        
        # 创建需要压缩的消息
        messages = []
        for i in range(15):
            messages.append(ChatMessage(
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                content="这是一条测试消息，包含足够多的内容用于测试压缩功能。" * 5,
                timestamp=datetime.now(),
            ))
        
        compacted, result = await compactor.compact(messages, force=True)
        
        # 验证结果
        assert result.original_messages == len(messages)
        assert result.compacted_messages <= result.original_messages
        assert result.compression_ratio >= 0
    
    @pytest.mark.asyncio
    async def test_prune_tool_outputs(self, compactor):
        """测试工具输出裁剪"""
        from backend.app.models.chat import ChatMessage, MessageRole
        
        # 创建包含长工具输出的消息
        messages = [
            ChatMessage(
                role=MessageRole.SYSTEM,
                content="x" * 500,  # 超过 max_tool_output_length
                metadata={"type": "tool_result"},
            ),
            ChatMessage(
                role=MessageRole.USER,
                content="短消息",
            ),
        ]
        
        pruned, count = compactor._prune_tool_outputs(messages)
        
        assert count == 1  # 一个消息被裁剪
        assert len(pruned[0].content) < 500
        assert pruned[0].metadata.get("truncated") is True
    
    def test_simple_summary(self, compactor):
        """测试简单摘要"""
        from backend.app.models.chat import ChatMessage, MessageRole
        
        messages = [
            ChatMessage(role=MessageRole.USER, content="请帮我分析代码"),
            ChatMessage(role=MessageRole.ASSISTANT, content="好的，我来分析"),
            ChatMessage(role=MessageRole.USER, content="谢谢"),
        ]
        
        summary = compactor._simple_summary(messages)
        
        assert summary is not None
        assert "用户请求" in summary
        assert len(summary) > 0


class TestEnhancedTools:
    """Phase 4: 增强工具测试"""
    
    @pytest.fixture
    def workspace_path(self, tmp_path):
        """创建测试工作区"""
        # 创建测试文件
        (tmp_path / "test.py").write_text("""
def hello_world():
    '''Say hello'''
    print("Hello, World!")
    
def calculate(a, b):
    '''Calculate sum'''
    return a + b
""")
        
        (tmp_path / "config.json").write_text('{"key": "value"}')
        
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "module.py").write_text("""
class MyClass:
    def method(self):
        pass
""")
        
        return tmp_path
    
    def test_grep_enhanced(self, workspace_path):
        """测试增强 Grep"""
        from backend.app.core.enhanced_tools import grep_enhanced
        
        result = grep_enhanced.invoke({
            "pattern": "def ",
            "path": str(workspace_path),
            "file_pattern": "*.py",
            "context_lines": 1,
        })
        
        assert "hello_world" in result or "calculate" in result
        assert "搜索结果" in result
    
    def test_glob_search(self, workspace_path):
        """测试 Glob 搜索"""
        from backend.app.core.enhanced_tools import glob_search
        
        result = glob_search.invoke({
            "pattern": "**/*.py",
            "path": str(workspace_path),
        })
        
        assert "test.py" in result
        assert "module.py" in result
    
    @pytest.mark.asyncio
    async def test_semantic_code_search(self, workspace_path):
        """测试语义代码搜索"""
        from backend.app.core.enhanced_tools import SemanticCodeSearch
        
        searcher = SemanticCodeSearch(str(workspace_path))
        results = await searcher.search(
            "print hello message",
            file_patterns=["*.py"],
            top_k=3,
            min_score=0.0,  # 允许所有结果
        )
        
        # 应该找到一些结果
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_multi_file_editor(self, workspace_path):
        """测试多文件编辑器"""
        from backend.app.core.enhanced_tools import MultiFileEditor, FileEdit
        
        editor = MultiFileEditor(str(workspace_path))
        
        # 测试 dry run
        edits = [
            FileEdit(
                file_path="test.py",
                old_content="Hello, World!",
                new_content="Hello, Universe!",
            ),
        ]
        
        result = await editor.edit_files(edits, dry_run=True)
        
        assert len(result.success) == 1
        
        # 验证文件未被修改
        content = (workspace_path / "test.py").read_text()
        assert "Hello, World!" in content
    
    @pytest.mark.asyncio
    async def test_search_and_replace(self, workspace_path):
        """测试搜索替换"""
        from backend.app.core.enhanced_tools import MultiFileEditor
        
        editor = MultiFileEditor(str(workspace_path))
        
        result = await editor.search_and_replace(
            pattern="def ",
            replacement="async def ",
            file_patterns=["*.py"],
            dry_run=True,
        )
        
        # 应该找到包含 "def " 的文件
        assert len(result.success) > 0
    
    def test_batch_executor(self):
        """测试批量执行器"""
        from backend.app.core.enhanced_tools import BatchExecutor, BatchOperation
        
        executor = BatchExecutor()
        
        # 注册测试工具
        def add(a: int, b: int) -> int:
            return a + b
        
        executor.register_tool("add", add)
        
        operations = [
            BatchOperation(tool_name="add", args={"a": 1, "b": 2}, id="op1"),
            BatchOperation(tool_name="add", args={"a": 3, "b": 4}, id="op2"),
        ]
        
        result = asyncio.run(executor.execute(operations))
        
        assert result.total == 2
        assert result.success_count == 2
        assert result.failed_count == 0


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_orchestrator_with_compaction(self):
        """测试编排器与压缩集成"""
        # 跳过需要 LLM 的测试
        pytest.skip("需要 LLM 客户端")
    
    def test_tools_registration(self):
        """测试工具注册"""
        from backend.app.core.enhanced_tools import get_enhanced_tools
        
        tools = get_enhanced_tools()
        
        assert len(tools) >= 5
        
        tool_names = [t.name for t in tools]
        assert "grep_enhanced" in tool_names
        assert "glob_search" in tool_names


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


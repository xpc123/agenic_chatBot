# -*- coding: utf-8 -*-
"""
工具调用测试

测试工具系统的功能：
- 工具注册
- 工具执行
- 参数验证
- 错误处理
- 批量执行
"""
import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import json
import tempfile
import os

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


@pytest.fixture
def temp_workspace(tmp_path):
    """创建临时工作区"""
    # 创建测试文件
    (tmp_path / "test.py").write_text("""
def hello():
    print("Hello, World!")

def calculate(a, b):
    return a + b

class MyClass:
    def method(self):
        pass
""")
    
    (tmp_path / "config.json").write_text('{"key": "value", "port": 8080}')
    
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "module.py").write_text("""
def nested_function():
    return "nested"
""")
    
    (tmp_path / "README.md").write_text("# Test Project\n\nThis is a test.")
    
    return tmp_path


class TestPracticalTools:
    """测试实用工具"""
    
    def test_read_file(self, temp_workspace):
        """测试读取文件"""
        from app.core.practical_tools import read_file_tool
        
        result = read_file_tool.invoke({
            "path": str(temp_workspace / "test.py"),
        })
        
        assert "hello" in result
        assert "calculate" in result
    
    def test_read_file_not_found(self, temp_workspace):
        """测试读取不存在的文件"""
        from app.core.practical_tools import read_file_tool
        
        result = read_file_tool.invoke({
            "path": str(temp_workspace / "not_exist.py"),
        })
        
        assert "error" in result.lower() or "not found" in result.lower()
    
    def test_write_file(self, temp_workspace):
        """测试写入文件"""
        from app.core.practical_tools import write_file_tool
        
        new_file = temp_workspace / "new_file.txt"
        
        result = write_file_tool.invoke({
            "path": str(new_file),
            "content": "Hello, World!",
        })
        
        assert new_file.exists()
        assert new_file.read_text() == "Hello, World!"
    
    def test_list_dir(self, temp_workspace):
        """测试列出目录"""
        from app.core.practical_tools import list_dir_tool
        
        result = list_dir_tool.invoke({
            "path": str(temp_workspace),
        })
        
        assert "test.py" in result
        assert "config.json" in result
        assert "subdir" in result
    
    def test_run_command(self):
        """测试运行命令"""
        from app.core.practical_tools import run_command_tool
        
        result = run_command_tool.invoke({
            "command": "echo 'Hello, World!'",
        })
        
        assert "Hello" in result


class TestEnhancedTools:
    """测试增强工具"""
    
    def test_grep_enhanced(self, temp_workspace):
        """测试增强 Grep"""
        from app.core.enhanced_tools import grep_enhanced
        
        result = grep_enhanced.invoke({
            "pattern": "def ",
            "path": str(temp_workspace),
            "file_pattern": "*.py",
            "context_lines": 1,
        })
        
        assert "hello" in result or "calculate" in result
    
    def test_glob_search(self, temp_workspace):
        """测试 Glob 搜索"""
        from app.core.enhanced_tools import glob_search
        
        result = glob_search.invoke({
            "pattern": "**/*.py",
            "path": str(temp_workspace),
        })
        
        assert "test.py" in result
        assert "module.py" in result
    
    def test_glob_search_specific_pattern(self, temp_workspace):
        """测试特定模式的 Glob 搜索"""
        from app.core.enhanced_tools import glob_search
        
        result = glob_search.invoke({
            "pattern": "*.json",
            "path": str(temp_workspace),
        })
        
        assert "config.json" in result


class TestSemanticCodeSearch:
    """测试语义代码搜索"""
    
    @pytest.mark.asyncio
    async def test_search_function(self, temp_workspace):
        """测试搜索函数"""
        from app.core.enhanced_tools import SemanticCodeSearch
        
        searcher = SemanticCodeSearch(str(temp_workspace))
        results = await searcher.search(
            query="print hello message",
            file_patterns=["*.py"],
            top_k=3,
            min_score=0.0,
        )
        
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_search_with_filter(self, temp_workspace):
        """测试带过滤的搜索"""
        from app.core.enhanced_tools import SemanticCodeSearch
        
        searcher = SemanticCodeSearch(str(temp_workspace))
        results = await searcher.search(
            query="nested function",
            file_patterns=["**/subdir/*.py"],
            top_k=5,
        )
        
        assert isinstance(results, list)


class TestMultiFileEditor:
    """测试多文件编辑器"""
    
    @pytest.mark.asyncio
    async def test_edit_single_file(self, temp_workspace):
        """测试编辑单个文件"""
        from app.core.enhanced_tools import MultiFileEditor, FileEdit
        
        editor = MultiFileEditor(str(temp_workspace))
        
        edits = [
            FileEdit(
                file_path="test.py",
                old_content="Hello, World!",
                new_content="Hello, Universe!",
            ),
        ]
        
        result = await editor.edit_files(edits, dry_run=True)
        
        assert len(result.success) == 1
        
        # 验证文件未被修改（dry run）
        content = (temp_workspace / "test.py").read_text()
        assert "Hello, World!" in content
    
    @pytest.mark.asyncio
    async def test_edit_multiple_files(self, temp_workspace):
        """测试编辑多个文件"""
        from app.core.enhanced_tools import MultiFileEditor, FileEdit
        
        editor = MultiFileEditor(str(temp_workspace))
        
        edits = [
            FileEdit(
                file_path="test.py",
                old_content="def hello",
                new_content="def say_hello",
            ),
            FileEdit(
                file_path="subdir/module.py",
                old_content="nested_function",
                new_content="deep_function",
            ),
        ]
        
        result = await editor.edit_files(edits, dry_run=True)
        
        assert len(result.success) >= 1
    
    @pytest.mark.asyncio
    async def test_search_and_replace(self, temp_workspace):
        """测试搜索替换"""
        from app.core.enhanced_tools import MultiFileEditor
        
        editor = MultiFileEditor(str(temp_workspace))
        
        result = await editor.search_and_replace(
            pattern="def ",
            replacement="async def ",
            file_patterns=["*.py"],
            dry_run=True,
        )
        
        assert len(result.success) >= 1


class TestBatchExecutor:
    """测试批量执行器"""
    
    def test_register_tool(self):
        """测试注册工具"""
        from app.core.enhanced_tools import BatchExecutor
        
        executor = BatchExecutor()
        
        def my_tool(x: int) -> int:
            return x * 2
        
        executor.register_tool("my_tool", my_tool)
        
        assert "my_tool" in executor.tools
    
    @pytest.mark.asyncio
    async def test_execute_batch(self):
        """测试批量执行"""
        from app.core.enhanced_tools import BatchExecutor, BatchOperation
        
        executor = BatchExecutor()
        
        def add(a: int, b: int) -> int:
            return a + b
        
        executor.register_tool("add", add)
        
        operations = [
            BatchOperation(tool_name="add", args={"a": 1, "b": 2}, id="op1"),
            BatchOperation(tool_name="add", args={"a": 3, "b": 4}, id="op2"),
        ]
        
        result = await executor.execute(operations)
        
        assert result.total == 2
        assert result.success_count == 2
    
    @pytest.mark.asyncio
    async def test_execute_with_error(self):
        """测试带错误的批量执行"""
        from app.core.enhanced_tools import BatchExecutor, BatchOperation
        
        executor = BatchExecutor()
        
        def failing_tool():
            raise ValueError("Intentional error")
        
        executor.register_tool("failing", failing_tool)
        
        operations = [
            BatchOperation(tool_name="failing", args={}, id="op1"),
        ]
        
        result = await executor.execute(operations)
        
        assert result.failed_count == 1


class TestToolValidation:
    """测试工具参数验证"""
    
    def test_required_parameter(self, temp_workspace):
        """测试必填参数"""
        from app.core.practical_tools import read_file_tool
        
        # 缺少 path 参数应该失败
        with pytest.raises(Exception):
            read_file_tool.invoke({})
    
    def test_parameter_type(self, temp_workspace):
        """测试参数类型"""
        from app.core.enhanced_tools import grep_enhanced
        
        # context_lines 应该是整数
        result = grep_enhanced.invoke({
            "pattern": "def",
            "path": str(temp_workspace),
            "context_lines": 2,  # 正确的类型
        })
        
        assert isinstance(result, str)


class TestToolErrorHandling:
    """测试工具错误处理"""
    
    def test_handle_file_not_found(self, temp_workspace):
        """测试处理文件不存在"""
        from app.core.practical_tools import read_file_tool
        
        result = read_file_tool.invoke({
            "path": "/nonexistent/path/file.txt",
        })
        
        # 应该返回错误信息而不是崩溃
        assert "error" in result.lower() or "not found" in result.lower()
    
    def test_handle_permission_denied(self, temp_workspace):
        """测试处理权限拒绝"""
        from app.core.practical_tools import write_file_tool
        
        # 尝试写入只读位置
        result = write_file_tool.invoke({
            "path": "/root/test.txt",  # 通常没有权限
            "content": "test",
        })
        
        # 应该返回错误信息
        assert "error" in result.lower() or "permission" in result.lower() or "denied" in result.lower()
    
    def test_handle_invalid_pattern(self, temp_workspace):
        """测试处理无效模式"""
        from app.core.enhanced_tools import grep_enhanced
        
        # 无效的正则表达式
        result = grep_enhanced.invoke({
            "pattern": "[invalid(",
            "path": str(temp_workspace),
        })
        
        # 应该处理错误而不是崩溃
        assert isinstance(result, str)


class TestToolIntegration:
    """测试工具集成"""
    
    def test_get_practical_tools(self):
        """测试获取实用工具"""
        from app.core.practical_tools import get_practical_tools
        
        tools = get_practical_tools()
        
        assert len(tools) > 0
        
        tool_names = [t.name for t in tools]
        assert "read_file" in tool_names or "read_file_tool" in tool_names
    
    def test_get_enhanced_tools(self):
        """测试获取增强工具"""
        from app.core.enhanced_tools import get_enhanced_tools
        
        tools = get_enhanced_tools()
        
        assert len(tools) >= 2
        
        tool_names = [t.name for t in tools]
        assert "grep_enhanced" in tool_names
        assert "glob_search" in tool_names


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


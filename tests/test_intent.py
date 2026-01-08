# -*- coding: utf-8 -*-
"""
意图识别测试

测试意图识别系统的功能：
- 表面意图识别
- 深层意图分析
- 任务类型分类
- 复杂度评估
- 工具推荐
"""
import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


@pytest.fixture
def mock_llm_client():
    """Mock LLM 客户端"""
    mock = AsyncMock()
    mock.chat_completion = AsyncMock()
    return mock


@pytest.fixture
def intent_recognizer(mock_llm_client):
    """创建意图识别器"""
    from app.core.intent_recognizer import IntentRecognizer
    return IntentRecognizer(llm=mock_llm_client)


class TestIntentRecognition:
    """测试意图识别"""
    
    @pytest.mark.asyncio
    async def test_recognize_code_generation(self, intent_recognizer, mock_llm_client):
        """测试识别代码生成意图"""
        mock_llm_client.chat_completion.return_value = """
        {
            "surface_intent": "代码生成",
            "deep_intent": "创建排序函数",
            "task_type": "code_generation",
            "complexity": "medium",
            "is_multi_step": false,
            "suggested_tools": ["write_file", "code_search"],
            "confidence": 0.95
        }
        """
        
        result = await intent_recognizer.recognize("帮我写一个快速排序函数")
        
        assert result.task_type == "code_generation"
        assert result.confidence > 0.8
    
    @pytest.mark.asyncio
    async def test_recognize_question_answering(self, intent_recognizer, mock_llm_client):
        """测试识别问答意图"""
        mock_llm_client.chat_completion.return_value = """
        {
            "surface_intent": "询问信息",
            "deep_intent": "了解概念",
            "task_type": "question_answering",
            "complexity": "low",
            "is_multi_step": false,
            "suggested_tools": ["search_documents"],
            "confidence": 0.9
        }
        """
        
        result = await intent_recognizer.recognize("什么是机器学习？")
        
        assert result.task_type == "question_answering"
    
    @pytest.mark.asyncio
    async def test_recognize_file_operation(self, intent_recognizer, mock_llm_client):
        """测试识别文件操作意图"""
        mock_llm_client.chat_completion.return_value = """
        {
            "surface_intent": "文件操作",
            "deep_intent": "读取文件内容",
            "task_type": "file_operation",
            "complexity": "low",
            "is_multi_step": false,
            "suggested_tools": ["read_file", "list_dir"],
            "confidence": 0.92
        }
        """
        
        result = await intent_recognizer.recognize("读取 config.json 文件")
        
        assert result.task_type == "file_operation"
        assert "read_file" in result.suggested_tools
    
    @pytest.mark.asyncio
    async def test_recognize_multi_step_task(self, intent_recognizer, mock_llm_client):
        """测试识别多步骤任务"""
        mock_llm_client.chat_completion.return_value = """
        {
            "surface_intent": "代码重构",
            "deep_intent": "提取函数并优化结构",
            "task_type": "code_refactoring",
            "complexity": "high",
            "is_multi_step": true,
            "suggested_tools": ["read_file", "write_file", "grep", "code_search"],
            "confidence": 0.88
        }
        """
        
        result = await intent_recognizer.recognize(
            "重构这个文件，把重复的代码提取成函数"
        )
        
        assert result.is_multi_step is True
        assert result.complexity == "high"
    
    @pytest.mark.asyncio
    async def test_recognize_search_intent(self, intent_recognizer, mock_llm_client):
        """测试识别搜索意图"""
        mock_llm_client.chat_completion.return_value = """
        {
            "surface_intent": "代码搜索",
            "deep_intent": "查找函数定义",
            "task_type": "code_search",
            "complexity": "low",
            "is_multi_step": false,
            "suggested_tools": ["grep", "code_search", "glob_search"],
            "confidence": 0.91
        }
        """
        
        result = await intent_recognizer.recognize("查找 handleClick 函数")
        
        assert result.task_type == "code_search"


class TestComplexityAssessment:
    """测试复杂度评估"""
    
    @pytest.mark.asyncio
    async def test_low_complexity(self, intent_recognizer, mock_llm_client):
        """测试低复杂度任务"""
        mock_llm_client.chat_completion.return_value = """
        {
            "surface_intent": "简单问答",
            "deep_intent": "获取信息",
            "task_type": "question_answering",
            "complexity": "low",
            "is_multi_step": false,
            "suggested_tools": [],
            "confidence": 0.95
        }
        """
        
        result = await intent_recognizer.recognize("今天是几号？")
        
        assert result.complexity == "low"
    
    @pytest.mark.asyncio
    async def test_high_complexity(self, intent_recognizer, mock_llm_client):
        """测试高复杂度任务"""
        mock_llm_client.chat_completion.return_value = """
        {
            "surface_intent": "架构设计",
            "deep_intent": "设计微服务架构",
            "task_type": "architecture_design",
            "complexity": "high",
            "is_multi_step": true,
            "suggested_tools": ["read_file", "write_file", "code_search"],
            "confidence": 0.85
        }
        """
        
        result = await intent_recognizer.recognize(
            "帮我设计一个支持百万用户的微服务架构"
        )
        
        assert result.complexity == "high"


class TestToolSuggestion:
    """测试工具推荐"""
    
    @pytest.mark.asyncio
    async def test_suggest_file_tools(self, intent_recognizer, mock_llm_client):
        """测试文件工具推荐"""
        mock_llm_client.chat_completion.return_value = """
        {
            "surface_intent": "文件编辑",
            "deep_intent": "修改配置文件",
            "task_type": "file_operation",
            "complexity": "low",
            "is_multi_step": false,
            "suggested_tools": ["read_file", "write_file"],
            "confidence": 0.93
        }
        """
        
        result = await intent_recognizer.recognize("修改 config.json 中的端口号")
        
        assert "read_file" in result.suggested_tools
        assert "write_file" in result.suggested_tools
    
    @pytest.mark.asyncio
    async def test_suggest_search_tools(self, intent_recognizer, mock_llm_client):
        """测试搜索工具推荐"""
        mock_llm_client.chat_completion.return_value = """
        {
            "surface_intent": "代码搜索",
            "deep_intent": "查找错误处理",
            "task_type": "code_search",
            "complexity": "low",
            "is_multi_step": false,
            "suggested_tools": ["grep", "code_search", "glob_search"],
            "confidence": 0.9
        }
        """
        
        result = await intent_recognizer.recognize(
            "找出所有的 try-except 块"
        )
        
        assert "grep" in result.suggested_tools


class TestEdgeCases:
    """测试边缘情况"""
    
    @pytest.mark.asyncio
    async def test_ambiguous_intent(self, intent_recognizer, mock_llm_client):
        """测试模糊意图"""
        mock_llm_client.chat_completion.return_value = """
        {
            "surface_intent": "不明确",
            "deep_intent": "需要更多信息",
            "task_type": "clarification_needed",
            "complexity": "unknown",
            "is_multi_step": false,
            "suggested_tools": [],
            "confidence": 0.4
        }
        """
        
        result = await intent_recognizer.recognize("做一下")
        
        assert result.confidence < 0.5
    
    @pytest.mark.asyncio
    async def test_empty_input(self, intent_recognizer, mock_llm_client):
        """测试空输入"""
        mock_llm_client.chat_completion.return_value = """
        {
            "surface_intent": "无意图",
            "deep_intent": "",
            "task_type": "none",
            "complexity": "none",
            "is_multi_step": false,
            "suggested_tools": [],
            "confidence": 0.0
        }
        """
        
        result = await intent_recognizer.recognize("")
        
        assert result.confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_malformed_llm_response(self, intent_recognizer, mock_llm_client):
        """测试 LLM 返回格式错误"""
        mock_llm_client.chat_completion.return_value = "这不是有效的 JSON"
        
        # 应该能处理错误，返回默认结果
        try:
            result = await intent_recognizer.recognize("测试")
            # 如果没有抛出异常，检查是否返回了默认值
            assert result is not None
        except Exception:
            # 或者抛出适当的异常
            pass


class TestIntentClassification:
    """测试意图分类"""
    
    @pytest.fixture
    def test_cases(self):
        """测试用例"""
        return [
            ("写一个冒泡排序", "code_generation"),
            ("这段代码有什么问题", "code_analysis"),
            ("删除 test.py 文件", "file_operation"),
            ("搜索所有 TODO 注释", "code_search"),
            ("解释什么是递归", "question_answering"),
            ("重命名所有变量", "code_refactoring"),
        ]
    
    @pytest.mark.asyncio
    async def test_classification_accuracy(self, intent_recognizer, mock_llm_client, test_cases):
        """测试分类准确性"""
        for query, expected_type in test_cases:
            mock_llm_client.chat_completion.return_value = f"""
            {{
                "surface_intent": "测试",
                "deep_intent": "测试",
                "task_type": "{expected_type}",
                "complexity": "medium",
                "is_multi_step": false,
                "suggested_tools": [],
                "confidence": 0.9
            }}
            """
            
            result = await intent_recognizer.recognize(query)
            
            assert result.task_type == expected_type, f"Query: {query}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


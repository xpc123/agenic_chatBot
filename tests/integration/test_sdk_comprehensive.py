# -*- coding: utf-8 -*-
"""
Agentic ChatBot SDK 综合测试套件

对标 Cursor / Claude Code / GitHub Copilot 的对话功能
测试各种场景和复杂度级别

运行方式:
    cd /ADE1/users/xpengche/project/agentic_chatBot
    source backend/venv/bin/activate
    python -m pytest tests/test_sdk_comprehensive.py -v
    
    # 或运行单个测试
    python tests/test_sdk_comprehensive.py
"""
import pytest
import asyncio
import time
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentic_sdk import ChatBot


# ============================================================================
# 测试配置
# ============================================================================

class TestComplexity(Enum):
    """测试复杂度级别"""
    TRIVIAL = "trivial"      # 最简单：问候、感谢
    LOW = "low"              # 低：简单问答
    MEDIUM = "medium"        # 中：需要工具
    HIGH = "high"            # 高：多步骤任务
    COMPLEX = "complex"      # 复杂：需要规划和推理


@dataclass
class TestCase:
    """测试用例"""
    id: str
    name: str
    description: str
    complexity: TestComplexity
    category: str
    input_message: str
    expected_behaviors: List[str]  # 期望的行为/输出特征
    follow_up_messages: List[str] = field(default_factory=list)  # 后续消息（测试上下文）
    requires_tools: List[str] = field(default_factory=list)  # 需要的工具
    timeout_seconds: int = 60
    

@dataclass 
class TestResult:
    """测试结果"""
    test_case: TestCase
    passed: bool
    duration_ms: float
    response: str
    tool_calls: List[str]
    errors: List[str]
    details: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 测试用例定义
# ============================================================================

TEST_CASES = [
    # ========== 1. 基础对话 (TRIVIAL) ==========
    TestCase(
        id="conv_001",
        name="简单问候",
        description="测试基本问候响应",
        complexity=TestComplexity.TRIVIAL,
        category="conversation",
        input_message="你好",
        expected_behaviors=["友好回复", "不调用工具"],
    ),
    TestCase(
        id="conv_002",
        name="英文问候",
        description="测试英文问候",
        complexity=TestComplexity.TRIVIAL,
        category="conversation",
        input_message="Hello!",
        expected_behaviors=["友好回复"],
    ),
    TestCase(
        id="conv_003",
        name="感谢回复",
        description="测试感谢语处理",
        complexity=TestComplexity.TRIVIAL,
        category="conversation",
        input_message="谢谢你的帮助",
        expected_behaviors=["礼貌回复", "不调用工具"],
    ),
    
    # ========== 2. 简单问答 (LOW) ==========
    TestCase(
        id="qa_001",
        name="常识问答",
        description="测试常识性问题回答",
        complexity=TestComplexity.LOW,
        category="qa",
        input_message="Python 是什么编程语言？",
        expected_behaviors=["准确描述Python", "提及动态类型或解释型"],
    ),
    TestCase(
        id="qa_002",
        name="技术概念",
        description="测试技术概念解释",
        complexity=TestComplexity.LOW,
        category="qa",
        input_message="什么是 REST API？",
        expected_behaviors=["解释REST", "提及HTTP方法"],
    ),
    TestCase(
        id="qa_003",
        name="代码解释",
        description="测试代码片段解释",
        complexity=TestComplexity.LOW,
        category="qa",
        input_message="解释这段代码: `for i in range(10): print(i)`",
        expected_behaviors=["解释循环", "解释range", "提及输出0-9"],
    ),
    
    # ========== 3. 文件操作 (MEDIUM) ==========
    TestCase(
        id="file_001",
        name="列出目录内容",
        description="测试目录列表功能",
        complexity=TestComplexity.MEDIUM,
        category="file_operation",
        input_message="帮我看看 /ADE1/users/xpengche/project/agentic_chatBot 目录下有什么",
        expected_behaviors=["调用list_directory", "显示文件列表", "显示目录结构"],
        requires_tools=["list_directory"],
    ),
    TestCase(
        id="file_002",
        name="读取文件内容",
        description="测试文件读取功能",
        complexity=TestComplexity.MEDIUM,
        category="file_operation",
        input_message="读取 /ADE1/users/xpengche/project/agentic_chatBot/README.md 的内容",
        expected_behaviors=["调用file_read", "显示文件内容"],
        requires_tools=["file_read_enhanced"],
    ),
    TestCase(
        id="file_003",
        name="项目分析",
        description="测试项目结构分析",
        complexity=TestComplexity.MEDIUM,
        category="file_operation",
        input_message="分析 /ADE1/users/xpengche/project/ContexBuilder 这个项目的结构",
        expected_behaviors=["调用list_directory", "描述项目结构", "识别项目类型"],
        requires_tools=["list_directory"],
    ),
    TestCase(
        id="file_004",
        name="查找特定文件",
        description="测试带过滤的目录列表",
        complexity=TestComplexity.MEDIUM,
        category="file_operation",
        input_message="列出 /ADE1/users/xpengche/project/agentic_chatBot 目录下所有的 Python 文件",
        expected_behaviors=["显示.py文件"],
        requires_tools=["list_directory"],
    ),
    
    # ========== 4. 系统操作 (MEDIUM) ==========
    TestCase(
        id="sys_001",
        name="环境信息",
        description="测试获取环境信息",
        complexity=TestComplexity.MEDIUM,
        category="system",
        input_message="告诉我当前的系统环境信息",
        expected_behaviors=["调用env_info", "显示系统信息"],
        requires_tools=["env_info"],
    ),
    TestCase(
        id="sys_002",
        name="进程列表",
        description="测试获取进程列表",
        complexity=TestComplexity.MEDIUM,
        category="system",
        input_message="列出当前运行的进程",
        expected_behaviors=["调用process_list", "显示进程信息"],
        requires_tools=["process_list"],
    ),
    TestCase(
        id="sys_003",
        name="执行简单命令",
        description="测试Shell命令执行",
        complexity=TestComplexity.MEDIUM,
        category="system",
        input_message="执行命令 `pwd` 告诉我当前目录",
        expected_behaviors=["调用shell_execute", "显示目录路径"],
        requires_tools=["shell_execute"],
    ),
    
    # ========== 5. 上下文记忆 (MEDIUM) ==========
    TestCase(
        id="mem_001",
        name="上下文记忆-基础",
        description="测试对话上下文记忆",
        complexity=TestComplexity.MEDIUM,
        category="memory",
        input_message="我正在开发一个叫 SuperApp 的项目",
        expected_behaviors=["确认理解"],
        follow_up_messages=[
            "这个项目用的是什么技术栈？",  # 应该问的是 SuperApp
        ],
    ),
    TestCase(
        id="mem_002",
        name="上下文记忆-文件操作",
        description="测试文件操作后的上下文记忆",
        complexity=TestComplexity.MEDIUM,
        category="memory",
        input_message="帮我看看 /ADE1/users/xpengche/project/ContexBuilder 目录",
        expected_behaviors=["列出目录"],
        follow_up_messages=[
            "这个项目是做什么的？",  # 应该基于之前看到的内容回答
        ],
        requires_tools=["list_directory"],
    ),
    
    # ========== 6. 代码分析 (HIGH) ==========
    TestCase(
        id="code_001",
        name="代码文件分析",
        description="测试代码文件分析能力",
        complexity=TestComplexity.HIGH,
        category="code_analysis",
        input_message="分析 /ADE1/users/xpengche/project/agentic_chatBot/agentic_sdk/chatbot.py 这个文件的主要功能",
        expected_behaviors=["读取文件", "识别类和函数", "描述功能"],
        requires_tools=["file_read_enhanced"],
    ),
    TestCase(
        id="code_002",
        name="代码问题诊断",
        description="测试代码问题识别",
        complexity=TestComplexity.HIGH,
        category="code_analysis",
        input_message="检查 /ADE1/users/xpengche/project/agentic_chatBot/backend/app/core/cursor_style_orchestrator.py 是否有明显的代码问题",
        expected_behaviors=["读取文件", "分析代码"],
        requires_tools=["file_read_enhanced"],
    ),
    
    # ========== 7. 复杂多步骤任务 (COMPLEX) ==========
    TestCase(
        id="complex_001",
        name="项目综合分析",
        description="测试项目综合分析（需要多个工具）",
        complexity=TestComplexity.COMPLEX,
        category="complex_task",
        input_message="全面分析 /ADE1/users/xpengche/project/ContexBuilder 项目，包括：目录结构、主要功能、技术栈、README内容",
        expected_behaviors=["多次工具调用", "综合分析报告"],
        requires_tools=["list_directory", "file_read_enhanced"],
        timeout_seconds=120,
    ),
    
    # ========== 8. 错误处理 ==========
    TestCase(
        id="err_001",
        name="无效路径处理",
        description="测试无效路径的错误处理",
        complexity=TestComplexity.MEDIUM,
        category="error_handling",
        input_message="读取 /nonexistent/path/file.txt 文件",
        expected_behaviors=["优雅的错误提示", "不崩溃"],
        requires_tools=["file_read_enhanced"],
    ),
    TestCase(
        id="err_002",
        name="空输入处理",
        description="测试空输入处理",
        complexity=TestComplexity.TRIVIAL,
        category="error_handling",
        input_message="   ",
        expected_behaviors=["提示输入为空或忽略"],
    ),
    
    # ========== 9. 边界情况 ==========
    TestCase(
        id="edge_001",
        name="中英文混合",
        description="测试中英文混合输入",
        complexity=TestComplexity.LOW,
        category="edge_case",
        input_message="帮我 explain 一下 Python 的 decorator 是什么",
        expected_behaviors=["理解混合语言", "解释装饰器"],
    ),
    TestCase(
        id="edge_002",
        name="特殊字符路径",
        description="测试包含特殊字符的路径",
        complexity=TestComplexity.MEDIUM,
        category="edge_case",
        input_message="列出 /tmp 目录",
        expected_behaviors=["正常处理"],
        requires_tools=["list_directory"],
    ),
    TestCase(
        id="edge_003",
        name="长消息处理",
        description="测试较长消息的处理",
        complexity=TestComplexity.LOW,
        category="edge_case",
        input_message="我需要你帮我分析一下这个问题：" + "这是一个非常长的描述，" * 20 + "请问你能理解吗？",
        expected_behaviors=["正常处理长消息"],
    ),
    
    # ========== 10. 对标 Cursor/Copilot 的能力 ==========
    TestCase(
        id="cursor_001",
        name="代码生成建议",
        description="测试代码生成/建议能力",
        complexity=TestComplexity.MEDIUM,
        category="cursor_like",
        input_message="帮我写一个 Python 函数，实现快速排序算法",
        expected_behaviors=["生成代码", "包含quicksort", "代码正确"],
    ),
    TestCase(
        id="cursor_002",
        name="代码重构建议",
        description="测试代码重构建议",
        complexity=TestComplexity.HIGH,
        category="cursor_like",
        input_message="""帮我优化这段代码:
```python
def get_even(nums):
    result = []
    for n in nums:
        if n % 2 == 0:
            result.append(n)
    return result
```""",
        expected_behaviors=["提供优化建议", "可能使用列表推导式"],
    ),
    TestCase(
        id="cursor_003",
        name="Bug修复建议",
        description="测试Bug识别和修复建议",
        complexity=TestComplexity.HIGH,
        category="cursor_like",
        input_message="""这段代码有什么问题？
```python
def divide(a, b):
    return a / b
```""",
        expected_behaviors=["识别除零错误", "建议添加检查"],
    ),
]


# ============================================================================
# 测试执行器
# ============================================================================

class SDKTestRunner:
    """SDK 测试执行器"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.bot: Optional[ChatBot] = None
        self.results: List[TestResult] = []
        
    def setup(self):
        """初始化 ChatBot"""
        print("🚀 初始化 ChatBot SDK...")
        self.bot = ChatBot()
        print("✅ ChatBot 初始化完成")
        
    def teardown(self):
        """清理资源"""
        self.bot = None
        
    def run_single_test(self, test_case: TestCase, session_id: str) -> TestResult:
        """运行单个测试"""
        start_time = time.time()
        response_parts = []
        tool_calls = []
        errors = []
        
        try:
            # 发送主消息
            for chunk in self.bot.chat_stream(test_case.input_message, session_id):
                if chunk.type == "text":
                    response_parts.append(chunk.content or "")
                elif chunk.type == "tool_call":
                    tool_calls.append(chunk.content)
                elif chunk.type == "error":
                    errors.append(chunk.content)
                    
            # 发送后续消息（测试上下文）
            for follow_up in test_case.follow_up_messages:
                for chunk in self.bot.chat_stream(follow_up, session_id):
                    if chunk.type == "text":
                        response_parts.append(f"\n[Follow-up] {chunk.content or ''}")
                    elif chunk.type == "tool_call":
                        tool_calls.append(chunk.content)
                        
        except Exception as e:
            errors.append(str(e))
            
        duration_ms = (time.time() - start_time) * 1000
        response = "".join(response_parts)
        
        # 评估结果
        passed = self._evaluate_result(test_case, response, tool_calls, errors)
        
        return TestResult(
            test_case=test_case,
            passed=passed,
            duration_ms=duration_ms,
            response=response,
            tool_calls=tool_calls,
            errors=errors,
        )
        
    def _evaluate_result(
        self,
        test_case: TestCase,
        response: str,
        tool_calls: List[str],
        errors: List[str],
    ) -> bool:
        """评估测试结果"""
        # 有错误则失败（除非是测试错误处理）
        if errors and test_case.category != "error_handling":
            return False
            
        # 检查是否调用了必需的工具
        if test_case.requires_tools:
            tool_calls_text = " ".join(tool_calls).lower()
            for required_tool in test_case.requires_tools:
                if required_tool.lower() not in tool_calls_text:
                    # 宽松检查：也检查响应中是否提到工具结果
                    if required_tool.lower() not in response.lower():
                        return False
                        
        # 响应不能为空（除非测试空输入）
        if not response.strip() and test_case.id != "err_002":
            return False
            
        # 响应不能说"无法访问文件系统"（除非确实是无效路径测试）
        if "无法访问" in response and test_case.category == "file_operation":
            if test_case.id != "err_001":
                return False
                
        return True
        
    def run_all_tests(self, categories: Optional[List[str]] = None) -> Dict[str, Any]:
        """运行所有测试"""
        self.setup()
        
        # 过滤测试用例
        test_cases = TEST_CASES
        if categories:
            test_cases = [tc for tc in TEST_CASES if tc.category in categories]
            
        print(f"\n📋 共 {len(test_cases)} 个测试用例")
        print("=" * 60)
        
        passed_count = 0
        failed_count = 0
        
        for i, test_case in enumerate(test_cases, 1):
            session_id = f"test-{test_case.id}-{int(time.time())}"
            
            if self.verbose:
                print(f"\n[{i}/{len(test_cases)}] {test_case.id}: {test_case.name}")
                print(f"    复杂度: {test_case.complexity.value}")
                print(f"    消息: {test_case.input_message[:50]}...")
                
            result = self.run_single_test(test_case, session_id)
            self.results.append(result)
            
            if result.passed:
                passed_count += 1
                if self.verbose:
                    print(f"    ✅ PASSED ({result.duration_ms:.0f}ms)")
            else:
                failed_count += 1
                if self.verbose:
                    print(f"    ❌ FAILED ({result.duration_ms:.0f}ms)")
                    if result.errors:
                        print(f"    错误: {result.errors}")
                    print(f"    响应: {result.response[:200]}...")
                    
        self.teardown()
        
        # 生成报告
        return self._generate_report(passed_count, failed_count)
        
    def _generate_report(self, passed: int, failed: int) -> Dict[str, Any]:
        """生成测试报告"""
        total = passed + failed
        
        print("\n" + "=" * 60)
        print("📊 测试报告")
        print("=" * 60)
        print(f"总计: {total} | 通过: {passed} | 失败: {failed}")
        print(f"通过率: {passed/total*100:.1f}%")
        
        # 按类别统计
        category_stats = {}
        for result in self.results:
            cat = result.test_case.category
            if cat not in category_stats:
                category_stats[cat] = {"passed": 0, "failed": 0}
            if result.passed:
                category_stats[cat]["passed"] += 1
            else:
                category_stats[cat]["failed"] += 1
                
        print("\n按类别统计:")
        for cat, stats in category_stats.items():
            total_cat = stats["passed"] + stats["failed"]
            print(f"  {cat}: {stats['passed']}/{total_cat}")
            
        # 失败用例详情
        failed_results = [r for r in self.results if not r.passed]
        if failed_results:
            print("\n❌ 失败用例详情:")
            for r in failed_results:
                print(f"\n  [{r.test_case.id}] {r.test_case.name}")
                print(f"  消息: {r.test_case.input_message[:80]}")
                print(f"  错误: {r.errors if r.errors else '无明确错误'}")
                print(f"  响应: {r.response[:150]}...")
                
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0,
            "category_stats": category_stats,
            "failed_cases": [r.test_case.id for r in failed_results],
        }


# ============================================================================
# Pytest 兼容
# ============================================================================

@pytest.fixture(scope="module")
def chatbot():
    """Pytest fixture: ChatBot 实例"""
    bot = ChatBot()
    yield bot


class TestConversation:
    """对话测试"""
    
    def test_greeting(self, chatbot):
        """测试问候"""
        response = ""
        for chunk in chatbot.chat_stream("你好", "pytest-conv-001"):
            if chunk.type == "text":
                response += chunk.content or ""
        assert response, "响应不应为空"
        assert "无法" not in response, "不应说无法处理"


class TestFileOperations:
    """文件操作测试"""
    
    def test_list_directory(self, chatbot):
        """测试目录列表"""
        response = ""
        tool_called = False
        for chunk in chatbot.chat_stream(
            "列出 /ADE1/users/xpengche/project/agentic_chatBot 目录",
            "pytest-file-001"
        ):
            if chunk.type == "text":
                response += chunk.content or ""
            if chunk.type == "tool_call":
                tool_called = True
                
        assert tool_called or "目录" in response or "文件" in response


class TestMemory:
    """记忆测试"""
    
    def test_context_memory(self, chatbot):
        """测试上下文记忆"""
        session_id = "pytest-mem-001"
        
        # 第一条消息
        for chunk in chatbot.chat_stream("我的名字是张三", session_id):
            pass
            
        # 第二条消息 - 应该记住名字
        response = ""
        for chunk in chatbot.chat_stream("我的名字是什么？", session_id):
            if chunk.type == "text":
                response += chunk.content or ""
                
        # 宽松检查 - 至少应该有响应
        assert response, "应该有响应"


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数 - 运行所有测试"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agentic ChatBot SDK 测试")
    parser.add_argument(
        "--category", "-c",
        type=str,
        nargs="+",
        help="只运行指定类别的测试",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=True,
        help="详细输出",
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="快速测试（只运行 TRIVIAL 和 LOW 复杂度）",
    )
    
    args = parser.parse_args()
    
    runner = SDKTestRunner(verbose=args.verbose)
    
    if args.quick:
        # 快速测试
        quick_cases = [
            tc for tc in TEST_CASES 
            if tc.complexity in [TestComplexity.TRIVIAL, TestComplexity.LOW]
        ]
        print(f"🏃 快速测试模式: {len(quick_cases)} 个用例")
        
    report = runner.run_all_tests(categories=args.category)
    
    # 返回退出码
    sys.exit(0 if report["failed"] == 0 else 1)


if __name__ == "__main__":
    main()


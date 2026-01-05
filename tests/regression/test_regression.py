# -*- coding: utf-8 -*-
"""
回归测试套件

确保核心功能不会因代码变更而退化。
每次提交/发布前必须通过所有 P0 级别的回归测试。

运行方式:
    pytest tests/regression/test_regression.py -v
    pytest tests/regression/test_regression.py -v -k "P0"  # 只运行 P0
"""
import pytest
import json
import time
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agentic_sdk import ChatBot


# ============================================================================
# 加载黄金用例
# ============================================================================

def load_golden_cases() -> List[Dict]:
    """加载黄金用例"""
    golden_file = Path(__file__).parent / "golden_cases.json"
    with open(golden_file, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("cases", [])


GOLDEN_CASES = load_golden_cases()


# ============================================================================
# 回归测试类
# ============================================================================

@dataclass
class RegressionResult:
    """回归测试结果"""
    case_id: str
    passed: bool
    latency_ms: float
    response: str
    tool_calls: List[str]
    failures: List[str]


class RegressionTester:
    """回归测试器"""
    
    def __init__(self, bot: ChatBot):
        self.bot = bot
        self.results: List[RegressionResult] = []
        
    def run_case(self, case: Dict) -> RegressionResult:
        """运行单个回归用例"""
        start_time = time.time()
        response_parts = []
        tool_calls = []
        failures = []
        
        try:
            session_id = f"regression-{case['id']}"
            
            for chunk in self.bot.chat_stream(case["input"], session_id):
                if chunk.type == "text":
                    response_parts.append(chunk.content or "")
                elif chunk.type == "tool_call":
                    tool_calls.append(chunk.content)
                    
        except Exception as e:
            failures.append(f"执行异常: {str(e)}")
            
        latency_ms = (time.time() - start_time) * 1000
        response = "".join(response_parts).lower()
        
        expected = case.get("expected", {})
        
        # 检查必须包含的关键词
        for keyword in expected.get("should_contain", []):
            if keyword.lower() not in response:
                failures.append(f"缺少关键词: {keyword}")
                
        # 检查不应包含的关键词
        for keyword in expected.get("should_not_contain", []):
            if keyword.lower() in response:
                failures.append(f"包含禁止词: {keyword}")
                
        # 检查延迟
        max_latency = expected.get("max_latency_ms", 60000)
        if latency_ms > max_latency:
            failures.append(f"延迟过高: {latency_ms:.0f}ms > {max_latency}ms")
            
        # 检查工具调用
        expected_tools = expected.get("tool_calls", [])
        if expected_tools:
            tool_calls_text = " ".join(tool_calls).lower()
            for tool in expected_tools:
                if tool.lower() not in tool_calls_text:
                    failures.append(f"缺少工具调用: {tool}")
                    
        return RegressionResult(
            case_id=case["id"],
            passed=len(failures) == 0,
            latency_ms=latency_ms,
            response="".join(response_parts)[:500],
            tool_calls=tool_calls,
            failures=failures,
        )
        
    def run_all(self, priority_filter: str = None) -> Dict[str, Any]:
        """运行所有回归测试"""
        cases = GOLDEN_CASES
        if priority_filter:
            cases = [c for c in cases if c.get("priority") == priority_filter]
            
        self.results = []
        passed = 0
        failed = 0
        
        for case in cases:
            result = self.run_case(case)
            self.results.append(result)
            
            if result.passed:
                passed += 1
            else:
                failed += 1
                
        return {
            "total": len(cases),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / len(cases) if cases else 0,
            "failed_cases": [r.case_id for r in self.results if not r.passed],
        }


# ============================================================================
# Pytest 测试用例
# ============================================================================

@pytest.fixture(scope="module")
def regression_bot():
    """回归测试用 ChatBot"""
    return ChatBot()


@pytest.fixture(scope="module")
def regression_tester(regression_bot):
    """回归测试器"""
    return RegressionTester(regression_bot)


# 为每个黄金用例生成测试
@pytest.mark.regression
@pytest.mark.parametrize("case", GOLDEN_CASES, ids=[c["id"] for c in GOLDEN_CASES])
def test_golden_case(regression_bot, case):
    """
    测试黄金用例
    
    每个用例单独作为一个测试，方便定位问题
    """
    tester = RegressionTester(regression_bot)
    result = tester.run_case(case)
    
    # 断言
    assert result.passed, f"回归测试失败: {case['id']}\n失败原因: {result.failures}"


# P0 级别测试（必须通过）
@pytest.mark.regression
class TestP0Regression:
    """P0 级别回归测试 - 核心功能"""
    
    @pytest.fixture(autouse=True)
    def setup(self, regression_bot):
        self.bot = regression_bot
        self.tester = RegressionTester(regression_bot)
        
    def test_greeting(self):
        """问候功能"""
        case = next(c for c in GOLDEN_CASES if c["id"] == "golden_001")
        result = self.tester.run_case(case)
        assert result.passed, f"问候失败: {result.failures}"
        
    def test_list_directory(self):
        """目录列表功能"""
        case = next(c for c in GOLDEN_CASES if c["id"] == "golden_002")
        result = self.tester.run_case(case)
        assert result.passed, f"目录列表失败: {result.failures}"
        
    def test_file_read(self):
        """文件读取功能"""
        case = next(c for c in GOLDEN_CASES if c["id"] == "golden_003")
        result = self.tester.run_case(case)
        assert result.passed, f"文件读取失败: {result.failures}"
        
    def test_shell_execute(self):
        """Shell 执行功能"""
        case = next(c for c in GOLDEN_CASES if c["id"] == "golden_004")
        result = self.tester.run_case(case)
        assert result.passed, f"Shell 执行失败: {result.failures}"


# ============================================================================
# 命令行入口
# ============================================================================

def main():
    """命令行运行"""
    import argparse
    
    parser = argparse.ArgumentParser(description="回归测试")
    parser.add_argument("--priority", "-p", choices=["P0", "P1", "P2"], help="只运行指定优先级")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    print("🔄 Agentic ChatBot 回归测试")
    print("=" * 60)
    
    bot = ChatBot()
    tester = RegressionTester(bot)
    
    report = tester.run_all(priority_filter=args.priority)
    
    print(f"\n📊 测试结果")
    print(f"总计: {report['total']} | 通过: {report['passed']} | 失败: {report['failed']}")
    print(f"通过率: {report['pass_rate']:.1%}")
    
    if report['failed_cases']:
        print(f"\n❌ 失败用例:")
        for case_id in report['failed_cases']:
            result = next(r for r in tester.results if r.case_id == case_id)
            print(f"  [{case_id}] {result.failures}")
            
    # 返回退出码
    sys.exit(0 if report['failed'] == 0 else 1)


if __name__ == "__main__":
    main()


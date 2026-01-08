# -*- coding: utf-8 -*-
"""
ChatBot 能力评估框架

评估维度：
1. 对话质量 - 回答的相关性、准确性、完整性
2. 意图理解 - 正确识别用户意图
3. 上下文保持 - 多轮对话中的记忆能力
4. 工具使用 - 正确调用和使用工具
5. 知识检索 - RAG 检索的准确性
6. 响应速度 - 延迟和吞吐量
7. 错误恢复 - 处理边缘情况的能力
"""
import json
import time
import requests
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
import statistics
from datetime import datetime


class EvaluationDimension(Enum):
    """评估维度"""
    RELEVANCE = "relevance"           # 相关性
    ACCURACY = "accuracy"             # 准确性
    COMPLETENESS = "completeness"     # 完整性
    CONTEXT_RETENTION = "context"     # 上下文保持
    TOOL_USAGE = "tools"              # 工具使用
    LATENCY = "latency"               # 响应延迟
    ERROR_HANDLING = "error"          # 错误处理


@dataclass
class EvaluationCase:
    """评估用例"""
    id: str
    name: str
    description: str
    dimension: EvaluationDimension
    messages: List[Dict[str, str]]  # 对话消息列表
    expected_behaviors: List[str]    # 期望行为
    scoring_fn: Optional[Callable] = None  # 自定义评分函数
    weight: float = 1.0              # 权重


@dataclass
class EvaluationResult:
    """评估结果"""
    case_id: str
    case_name: str
    dimension: str
    score: float  # 0-100
    passed: bool
    latency_ms: float
    details: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class ChatBotEvaluator:
    """ChatBot 评估器"""
    
    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.results: List[EvaluationResult] = []
    
    def check_backend(self) -> bool:
        """检查后端是否可用"""
        try:
            response = self.session.get(f"{self.backend_url}/health", timeout=5)
            return response.status_code in [200, 503]
        except:
            return False
    
    def send_message(self, message: str, session_id: str) -> Dict[str, Any]:
        """发送消息并返回响应"""
        start_time = time.time()
        
        try:
            response = self.session.post(
                f"{self.backend_url}/api/v2/chat/message",
                json={"message": message, "session_id": session_id},
                timeout=120
            )
            
            latency = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                data["_latency_ms"] = latency
                return data
            else:
                return {
                    "error": f"HTTP {response.status_code}",
                    "message": "",
                    "_latency_ms": latency
                }
        except Exception as e:
            return {
                "error": str(e),
                "message": "",
                "_latency_ms": (time.time() - start_time) * 1000
            }
    
    def evaluate_case(self, case: EvaluationCase) -> EvaluationResult:
        """评估单个用例"""
        session_id = f"eval-{case.id}-{int(time.time())}"
        responses = []
        total_latency = 0
        errors = []
        
        # 执行对话
        for msg in case.messages:
            response = self.send_message(msg["content"], session_id)
            responses.append(response)
            total_latency += response.get("_latency_ms", 0)
            
            if "error" in response and response["error"]:
                errors.append(response["error"])
        
        # 评分
        if case.scoring_fn:
            score, details = case.scoring_fn(case, responses)
        else:
            score, details = self._default_scoring(case, responses)
        
        return EvaluationResult(
            case_id=case.id,
            case_name=case.name,
            dimension=case.dimension.value,
            score=score,
            passed=score >= 60,
            latency_ms=total_latency / len(case.messages) if case.messages else 0,
            details=details,
            errors=errors
        )
    
    def _default_scoring(
        self, 
        case: EvaluationCase, 
        responses: List[Dict]
    ) -> tuple[float, Dict]:
        """默认评分逻辑"""
        score = 0
        details = {"checks": []}
        
        # 检查期望行为
        for expected in case.expected_behaviors:
            matched = False
            for resp in responses:
                msg = resp.get("message", "")
                if self._check_behavior(expected, msg, resp):
                    matched = True
                    break
            
            details["checks"].append({
                "expected": expected,
                "matched": matched
            })
            
            if matched:
                score += 100 / len(case.expected_behaviors)
        
        return score, details
    
    def _check_behavior(
        self, 
        expected: str, 
        message: str, 
        response: Dict
    ) -> bool:
        """检查期望行为是否满足"""
        expected_lower = expected.lower()
        message_lower = message.lower()
        
        # 关键词匹配
        if expected.startswith("contains:"):
            keyword = expected[9:].strip().lower()
            return keyword in message_lower
        
        # 长度检查
        if expected.startswith("length>"):
            min_len = int(expected[7:])
            return len(message) > min_len
        
        # 工具使用检查
        if expected.startswith("used_tool:"):
            tool_name = expected[10:].strip()
            used_tools = response.get("used_tools", [])
            return tool_name in used_tools
        
        # 无错误检查
        if expected == "no_error":
            return "error" not in response or not response["error"]
        
        # 默认：包含检查
        return expected_lower in message_lower
    
    def run_evaluation(
        self, 
        cases: List[EvaluationCase],
        verbose: bool = True
    ) -> Dict[str, Any]:
        """运行评估"""
        if not self.check_backend():
            return {"error": "Backend not available"}
        
        self.results = []
        
        for case in cases:
            if verbose:
                print(f"📋 Evaluating: {case.name}...")
            
            result = self.evaluate_case(case)
            self.results.append(result)
            
            if verbose:
                status = "✅" if result.passed else "❌"
                print(f"   {status} Score: {result.score:.1f}/100, "
                      f"Latency: {result.latency_ms:.0f}ms")
        
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """生成评估报告"""
        if not self.results:
            return {"error": "No results"}
        
        # 按维度分组
        by_dimension = {}
        for result in self.results:
            dim = result.dimension
            if dim not in by_dimension:
                by_dimension[dim] = []
            by_dimension[dim].append(result)
        
        # 计算各维度得分
        dimension_scores = {}
        for dim, results in by_dimension.items():
            scores = [r.score for r in results]
            dimension_scores[dim] = {
                "mean": statistics.mean(scores),
                "min": min(scores),
                "max": max(scores),
                "pass_rate": sum(1 for r in results if r.passed) / len(results) * 100
            }
        
        # 总体统计
        all_scores = [r.score for r in self.results]
        all_latencies = [r.latency_ms for r in self.results]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_cases": len(self.results),
            "passed_cases": sum(1 for r in self.results if r.passed),
            "overall_score": statistics.mean(all_scores),
            "overall_pass_rate": sum(1 for r in self.results if r.passed) / len(self.results) * 100,
            "avg_latency_ms": statistics.mean(all_latencies),
            "dimension_scores": dimension_scores,
            "results": [
                {
                    "case_id": r.case_id,
                    "name": r.case_name,
                    "dimension": r.dimension,
                    "score": r.score,
                    "passed": r.passed,
                    "latency_ms": r.latency_ms,
                    "errors": r.errors
                }
                for r in self.results
            ]
        }


# ==================== 预定义评估用例 ====================

STANDARD_EVALUATION_CASES = [
    # 相关性测试
    EvaluationCase(
        id="rel-001",
        name="简单问答 - Python 定义",
        description="测试对基础问题的回答相关性",
        dimension=EvaluationDimension.RELEVANCE,
        messages=[{"role": "user", "content": "什么是 Python？"}],
        expected_behaviors=["contains:python", "contains:编程", "length>50"]
    ),
    EvaluationCase(
        id="rel-002",
        name="代码生成请求",
        description="测试代码生成的相关性",
        dimension=EvaluationDimension.RELEVANCE,
        messages=[{"role": "user", "content": "写一个冒泡排序的 Python 代码"}],
        expected_behaviors=["contains:def", "contains:sort", "contains:for"]
    ),
    
    # 上下文保持测试
    EvaluationCase(
        id="ctx-001",
        name="记住用户名字",
        description="测试是否记住用户信息",
        dimension=EvaluationDimension.CONTEXT_RETENTION,
        messages=[
            {"role": "user", "content": "我叫小明"},
            {"role": "user", "content": "我叫什么名字？"}
        ],
        expected_behaviors=["contains:小明"]
    ),
    EvaluationCase(
        id="ctx-002",
        name="记住讨论话题",
        description="测试是否保持话题连续性",
        dimension=EvaluationDimension.CONTEXT_RETENTION,
        messages=[
            {"role": "user", "content": "我们来讨论机器学习"},
            {"role": "user", "content": "它的主要应用场景有哪些？"}
        ],
        expected_behaviors=["contains:机器学习", "no_error"]
    ),
    
    # 准确性测试
    EvaluationCase(
        id="acc-001",
        name="数学计算",
        description="测试简单计算的准确性",
        dimension=EvaluationDimension.ACCURACY,
        messages=[{"role": "user", "content": "2 + 2 等于几？"}],
        expected_behaviors=["contains:4"]
    ),
    EvaluationCase(
        id="acc-002",
        name="事实查询",
        description="测试常识性问题的准确性",
        dimension=EvaluationDimension.ACCURACY,
        messages=[{"role": "user", "content": "Python 是什么时候创建的？"}],
        expected_behaviors=["contains:1991", "no_error"]
    ),
    
    # 错误处理测试
    EvaluationCase(
        id="err-001",
        name="空消息处理",
        description="测试空消息的处理",
        dimension=EvaluationDimension.ERROR_HANDLING,
        messages=[{"role": "user", "content": "   "}],
        expected_behaviors=["no_error", "length>0"]
    ),
    EvaluationCase(
        id="err-002",
        name="无意义输入处理",
        description="测试无意义输入的处理",
        dimension=EvaluationDimension.ERROR_HANDLING,
        messages=[{"role": "user", "content": "asdfghjkl"}],
        expected_behaviors=["no_error", "length>10"]
    ),
    
    # 完整性测试
    EvaluationCase(
        id="comp-001",
        name="多步骤任务说明",
        description="测试回答的完整性",
        dimension=EvaluationDimension.COMPLETENESS,
        messages=[{"role": "user", "content": "如何安装 Python？"}],
        expected_behaviors=["length>100", "no_error"]
    ),
]


def run_standard_evaluation(backend_url: str = "http://localhost:8000"):
    """运行标准评估"""
    evaluator = ChatBotEvaluator(backend_url)
    
    print("=" * 60)
    print("🤖 ChatBot 能力评估")
    print("=" * 60)
    print()
    
    report = evaluator.run_evaluation(STANDARD_EVALUATION_CASES)
    
    if "error" in report:
        print(f"❌ 评估失败: {report['error']}")
        return report
    
    print()
    print("=" * 60)
    print("📊 评估报告")
    print("=" * 60)
    print(f"总用例数: {report['total_cases']}")
    print(f"通过数: {report['passed_cases']}")
    print(f"总体得分: {report['overall_score']:.1f}/100")
    print(f"通过率: {report['overall_pass_rate']:.1f}%")
    print(f"平均延迟: {report['avg_latency_ms']:.0f}ms")
    print()
    print("各维度得分:")
    for dim, scores in report['dimension_scores'].items():
        print(f"  {dim}: {scores['mean']:.1f}/100 "
              f"(通过率: {scores['pass_rate']:.0f}%)")
    
    return report


if __name__ == "__main__":
    run_standard_evaluation()



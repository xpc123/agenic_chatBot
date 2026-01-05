# -*- coding: utf-8 -*-
"""
Agentic ChatBot 评估框架

基于业界标准的评估指标，对标:
- RAGAS (RAG Assessment)
- DeepEval
- SWE-Bench 思路

评估维度:
1. 工具使用准确性 (Tool Use Accuracy)
2. 响应相关性 (Response Relevancy)
3. 上下文利用率 (Context Utilization)
4. 任务完成率 (Task Completion Rate)
5. 响应延迟 (Latency)
6. 错误处理 (Error Handling)

用法:
    python -m tests.evaluation.eval_framework
"""
import time
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agentic_sdk import ChatBot


# ============================================================================
# 评估指标定义
# ============================================================================

class MetricType(Enum):
    """评估指标类型"""
    TOOL_USE_ACCURACY = "tool_use_accuracy"      # 工具使用准确性
    RESPONSE_RELEVANCY = "response_relevancy"    # 响应相关性
    CONTEXT_UTILIZATION = "context_utilization"  # 上下文利用率
    TASK_COMPLETION = "task_completion"          # 任务完成率
    LATENCY = "latency"                          # 响应延迟
    ERROR_HANDLING = "error_handling"            # 错误处理


@dataclass
class EvalCase:
    """评估用例"""
    id: str
    query: str
    expected_tools: List[str] = field(default_factory=list)  # 期望调用的工具
    expected_keywords: List[str] = field(default_factory=list)  # 期望响应包含的关键词
    ground_truth: str = ""  # 标准答案（可选）
    context: Optional[str] = None  # 预设上下文
    max_latency_ms: int = 30000  # 最大延迟
    category: str = "general"


@dataclass
class EvalResult:
    """评估结果"""
    case_id: str
    metrics: Dict[str, float]
    response: str
    tool_calls: List[str]
    latency_ms: float
    errors: List[str]
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalReport:
    """评估报告"""
    total_cases: int
    passed_cases: int
    failed_cases: int
    metrics_summary: Dict[str, float]
    category_breakdown: Dict[str, Dict[str, float]]
    results: List[EvalResult]
    timestamp: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self, path: str) -> None:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


# ============================================================================
# 评估用例集
# ============================================================================

EVAL_CASES = [
    # ========== 工具使用评估 ==========
    EvalCase(
        id="tool_001",
        query="列出 /tmp 目录下的文件",
        expected_tools=["list_directory"],
        expected_keywords=["目录", "文件"],
        category="tool_use",
    ),
    EvalCase(
        id="tool_002",
        query="读取 /etc/hostname 文件的内容",
        expected_tools=["file_read_enhanced"],
        expected_keywords=["hostname", "文件"],
        category="tool_use",
    ),
    EvalCase(
        id="tool_003",
        query="执行命令 `whoami` 查看当前用户",
        expected_tools=["shell_execute"],
        expected_keywords=["用户"],
        category="tool_use",
    ),
    EvalCase(
        id="tool_004",
        query="告诉我当前系统环境信息",
        expected_tools=["env_info"],
        expected_keywords=["系统", "环境"],
        category="tool_use",
    ),
    
    # ========== 响应相关性评估 ==========
    EvalCase(
        id="rel_001",
        query="什么是 Python 装饰器？",
        expected_keywords=["decorator", "函数", "包装", "@"],
        category="relevancy",
    ),
    EvalCase(
        id="rel_002",
        query="解释 REST API 的设计原则",
        expected_keywords=["HTTP", "资源", "状态", "GET", "POST"],
        category="relevancy",
    ),
    
    # ========== 上下文利用评估 ==========
    EvalCase(
        id="ctx_001",
        query="我的名字是什么？",
        context="用户之前说：我叫张三，是一名软件工程师。",
        expected_keywords=["张三"],
        category="context",
    ),
    
    # ========== 任务完成评估 ==========
    EvalCase(
        id="task_001",
        query="帮我写一个计算阶乘的 Python 函数",
        expected_keywords=["def", "factorial", "return"],
        category="task_completion",
    ),
    EvalCase(
        id="task_002",
        query="分析 /ADE1/users/xpengche/project/ContexBuilder 项目的结构",
        expected_tools=["list_directory"],
        expected_keywords=["src", "tests", "目录", "项目"],
        category="task_completion",
    ),
    
    # ========== 错误处理评估 ==========
    EvalCase(
        id="err_001",
        query="读取 /不存在的路径/文件.txt",
        expected_keywords=["不存在", "错误", "找不到"],
        category="error_handling",
    ),
]


# ============================================================================
# 评估器
# ============================================================================

class Evaluator:
    """评估器"""
    
    def __init__(self, bot: Optional[ChatBot] = None):
        self.bot = bot or ChatBot()
        self.results: List[EvalResult] = []
        
    def evaluate_case(self, case: EvalCase) -> EvalResult:
        """评估单个用例"""
        start_time = time.time()
        response_parts = []
        tool_calls = []
        errors = []
        
        try:
            session_id = f"eval-{case.id}"
            
            # 如果有预设上下文，先发送
            if case.context:
                for chunk in self.bot.chat_stream(case.context, session_id):
                    pass
            
            # 发送评估查询
            for chunk in self.bot.chat_stream(case.query, session_id):
                if chunk.type == "text":
                    response_parts.append(chunk.content or "")
                elif chunk.type == "tool_call":
                    tool_calls.append(chunk.content)
                elif chunk.type == "error":
                    errors.append(chunk.content)
                    
        except Exception as e:
            errors.append(str(e))
            
        latency_ms = (time.time() - start_time) * 1000
        response = "".join(response_parts)
        
        # 计算各项指标
        metrics = self._calculate_metrics(case, response, tool_calls, latency_ms, errors)
        
        # 判断是否通过
        passed = self._judge_pass(case, metrics, errors)
        
        return EvalResult(
            case_id=case.id,
            metrics=metrics,
            response=response,
            tool_calls=tool_calls,
            latency_ms=latency_ms,
            errors=errors,
            passed=passed,
        )
    
    def _calculate_metrics(
        self,
        case: EvalCase,
        response: str,
        tool_calls: List[str],
        latency_ms: float,
        errors: List[str],
    ) -> Dict[str, float]:
        """计算评估指标"""
        metrics = {}
        
        # 1. 工具使用准确性
        if case.expected_tools:
            tool_calls_text = " ".join(tool_calls).lower()
            matched = sum(1 for t in case.expected_tools if t.lower() in tool_calls_text)
            metrics["tool_use_accuracy"] = matched / len(case.expected_tools)
        else:
            metrics["tool_use_accuracy"] = 1.0  # 不需要工具则为满分
            
        # 2. 响应相关性（关键词匹配）
        if case.expected_keywords:
            response_lower = response.lower()
            matched = sum(1 for kw in case.expected_keywords if kw.lower() in response_lower)
            metrics["response_relevancy"] = matched / len(case.expected_keywords)
        else:
            metrics["response_relevancy"] = 1.0 if response else 0.0
            
        # 3. 延迟评分
        if latency_ms <= case.max_latency_ms:
            # 线性评分：越快越好
            metrics["latency_score"] = max(0, 1 - (latency_ms / case.max_latency_ms) * 0.5)
        else:
            metrics["latency_score"] = 0.0
            
        # 4. 错误处理
        if case.category == "error_handling":
            # 期望优雅处理错误
            metrics["error_handling"] = 1.0 if response and not any("异常" in e for e in errors) else 0.0
        else:
            metrics["error_handling"] = 0.0 if errors else 1.0
            
        return metrics
    
    def _judge_pass(
        self,
        case: EvalCase,
        metrics: Dict[str, float],
        errors: List[str],
    ) -> bool:
        """判断是否通过"""
        # 工具使用必须正确
        if case.expected_tools and metrics.get("tool_use_accuracy", 0) < 0.5:
            return False
            
        # 响应相关性至少 50%
        if metrics.get("response_relevancy", 0) < 0.5:
            return False
            
        # 非错误处理测试不应有错误
        if case.category != "error_handling" and errors:
            return False
            
        return True
    
    def run_evaluation(self, cases: Optional[List[EvalCase]] = None) -> EvalReport:
        """运行完整评估"""
        cases = cases or EVAL_CASES
        self.results = []
        
        print(f"\n📊 开始评估 ({len(cases)} 个用例)")
        print("=" * 60)
        
        for i, case in enumerate(cases, 1):
            print(f"[{i}/{len(cases)}] {case.id}: {case.query[:40]}...")
            result = self.evaluate_case(case)
            self.results.append(result)
            
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"  {status} (延迟: {result.latency_ms:.0f}ms)")
            
            if not result.passed:
                print(f"  工具准确性: {result.metrics.get('tool_use_accuracy', 0):.2f}")
                print(f"  响应相关性: {result.metrics.get('response_relevancy', 0):.2f}")
                
        return self._generate_report()
    
    def _generate_report(self) -> EvalReport:
        """生成评估报告"""
        from datetime import datetime
        
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        
        # 计算各指标平均值
        metrics_summary = {}
        all_metrics = ["tool_use_accuracy", "response_relevancy", "latency_score", "error_handling"]
        for metric in all_metrics:
            values = [r.metrics.get(metric, 0) for r in self.results]
            metrics_summary[metric] = sum(values) / len(values) if values else 0
            
        # 按类别统计
        category_breakdown = {}
        for result in self.results:
            case = next(c for c in EVAL_CASES if c.id == result.case_id)
            cat = case.category
            if cat not in category_breakdown:
                category_breakdown[cat] = {"passed": 0, "failed": 0, "total": 0}
            category_breakdown[cat]["total"] += 1
            if result.passed:
                category_breakdown[cat]["passed"] += 1
            else:
                category_breakdown[cat]["failed"] += 1
                
        # 计算通过率
        for cat in category_breakdown:
            total = category_breakdown[cat]["total"]
            category_breakdown[cat]["pass_rate"] = category_breakdown[cat]["passed"] / total if total else 0
            
        report = EvalReport(
            total_cases=len(self.results),
            passed_cases=passed,
            failed_cases=failed,
            metrics_summary=metrics_summary,
            category_breakdown=category_breakdown,
            results=self.results,
            timestamp=datetime.now().isoformat(),
        )
        
        # 打印报告
        print("\n" + "=" * 60)
        print("📊 评估报告")
        print("=" * 60)
        print(f"总计: {report.total_cases} | 通过: {passed} | 失败: {failed}")
        print(f"通过率: {passed/report.total_cases*100:.1f}%")
        
        print("\n指标摘要:")
        for metric, value in metrics_summary.items():
            print(f"  {metric}: {value:.2%}")
            
        print("\n按类别统计:")
        for cat, stats in category_breakdown.items():
            print(f"  {cat}: {stats['passed']}/{stats['total']} ({stats['pass_rate']:.0%})")
            
        return report


# ============================================================================
# LLM-as-Judge 评估器（高级）
# ============================================================================

class LLMJudge:
    """
    使用 LLM 作为评判者
    
    类似 RAGAS 的方法，使用另一个 LLM 来评估响应质量
    """
    
    def __init__(self, judge_bot: Optional[ChatBot] = None):
        self.judge = judge_bot or ChatBot()
        
    async def evaluate_response(
        self,
        query: str,
        response: str,
        ground_truth: Optional[str] = None,
    ) -> Dict[str, float]:
        """使用 LLM 评估响应"""
        
        prompt = f"""请评估以下 AI 助手的回答质量，给出 0-1 的分数。

用户问题: {query}

AI 回答:
{response}

{"标准答案: " + ground_truth if ground_truth else ""}

请从以下维度评分（0-1）：
1. 准确性 (accuracy): 信息是否准确
2. 完整性 (completeness): 是否完整回答了问题
3. 清晰度 (clarity): 表达是否清晰易懂
4. 有用性 (helpfulness): 对用户是否有帮助

请以 JSON 格式返回：
{{"accuracy": 0.X, "completeness": 0.X, "clarity": 0.X, "helpfulness": 0.X}}
"""
        
        try:
            result = ""
            for chunk in self.judge.chat_stream(prompt, "judge-session"):
                if chunk.type == "text":
                    result += chunk.content or ""
                    
            # 解析 JSON
            import re
            json_match = re.search(r'\{[^}]+\}', result)
            if json_match:
                scores = json.loads(json_match.group())
                return scores
        except Exception as e:
            print(f"LLM Judge error: {e}")
            
        return {"accuracy": 0.5, "completeness": 0.5, "clarity": 0.5, "helpfulness": 0.5}


# ============================================================================
# 主函数
# ============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Agentic ChatBot 评估")
    parser.add_argument("--category", "-c", help="只评估指定类别")
    parser.add_argument("--output", "-o", help="输出报告路径")
    
    args = parser.parse_args()
    
    evaluator = Evaluator()
    
    cases = EVAL_CASES
    if args.category:
        cases = [c for c in EVAL_CASES if c.category == args.category]
        
    report = evaluator.run_evaluation(cases)
    
    if args.output:
        report.to_json(args.output)
        print(f"\n📝 报告已保存到: {args.output}")


if __name__ == "__main__":
    main()


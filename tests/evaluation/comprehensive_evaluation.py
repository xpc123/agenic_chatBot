# -*- coding: utf-8 -*-
"""
综合评估套件

扩展标准评估用例，覆盖更多场景和边界条件。
"""
from chatbot_evaluation import (
    EvaluationCase, 
    EvaluationDimension, 
    ChatBotEvaluator,
    STANDARD_EVALUATION_CASES
)
from typing import List, Dict, Any
import statistics


# ==================== 1. 意图识别评估用例 ====================

INTENT_EVALUATION_CASES = [
    EvaluationCase(
        id="intent-001",
        name="编码请求识别",
        description="识别编程/编码意图",
        dimension=EvaluationDimension.ACCURACY,
        messages=[{"role": "user", "content": "帮我写一个快速排序算法"}],
        expected_behaviors=["contains:def", "contains:sort", "no_error"]
    ),
    EvaluationCase(
        id="intent-002",
        name="解释请求识别",
        description="识别解释/说明意图",
        dimension=EvaluationDimension.ACCURACY,
        messages=[{"role": "user", "content": "解释一下什么是递归"}],
        expected_behaviors=["contains:递归", "contains:函数", "length>100"]
    ),
    EvaluationCase(
        id="intent-003",
        name="调试请求识别",
        description="识别调试意图",
        dimension=EvaluationDimension.ACCURACY,
        messages=[{"role": "user", "content": "我的代码报错了：IndexError: list index out of range"}],
        expected_behaviors=["contains:索引", "no_error"]
    ),
    EvaluationCase(
        id="intent-004",
        name="优化请求识别",
        description="识别优化意图",
        dimension=EvaluationDimension.ACCURACY,
        messages=[{"role": "user", "content": "如何优化这段代码的性能？for i in range(len(arr)): print(arr[i])"}],
        expected_behaviors=["no_error", "length>50"]
    ),
    EvaluationCase(
        id="intent-005",
        name="对话意图识别",
        description="识别闲聊意图",
        dimension=EvaluationDimension.ACCURACY,
        messages=[{"role": "user", "content": "今天天气怎么样？"}],
        expected_behaviors=["no_error", "length>10"]
    ),
]


# ==================== 2. 多轮对话评估用例 ====================

MULTI_TURN_EVALUATION_CASES = [
    EvaluationCase(
        id="multi-001",
        name="三轮连续对话",
        description="测试三轮对话的上下文保持",
        dimension=EvaluationDimension.CONTEXT_RETENTION,
        messages=[
            {"role": "user", "content": "我正在学习 Python"},
            {"role": "user", "content": "有什么好的学习资源吗？"},
            {"role": "user", "content": "刚才说的第一个资源是什么？"}
        ],
        expected_behaviors=["no_error", "length>30"]
    ),
    EvaluationCase(
        id="multi-002",
        name="话题切换后回顾",
        description="测试话题切换后能否回顾之前的内容",
        dimension=EvaluationDimension.CONTEXT_RETENTION,
        messages=[
            {"role": "user", "content": "我在开发一个网站"},
            {"role": "user", "content": "对了，今天北京天气怎么样"},
            {"role": "user", "content": "回到网站的话题，你有什么建议？"}
        ],
        expected_behaviors=["contains:网站", "no_error"]
    ),
    EvaluationCase(
        id="multi-003",
        name="代码跟进问题",
        description="测试代码讨论的连续性",
        dimension=EvaluationDimension.CONTEXT_RETENTION,
        messages=[
            {"role": "user", "content": "写一个计算阶乘的函数"},
            {"role": "user", "content": "能用递归实现吗？"},
            {"role": "user", "content": "两种方式哪个效率更高？"}
        ],
        expected_behaviors=["no_error", "length>50"]
    ),
    EvaluationCase(
        id="multi-004",
        name="用户偏好记忆",
        description="测试是否记住用户偏好",
        dimension=EvaluationDimension.CONTEXT_RETENTION,
        messages=[
            {"role": "user", "content": "我喜欢简洁的代码风格"},
            {"role": "user", "content": "帮我写一个冒泡排序"}
        ],
        expected_behaviors=["contains:def", "no_error"]
    ),
]


# ==================== 3. 代码能力评估用例 ====================

CODE_EVALUATION_CASES = [
    EvaluationCase(
        id="code-001",
        name="基础函数生成",
        description="生成简单函数",
        dimension=EvaluationDimension.COMPLETENESS,
        messages=[{"role": "user", "content": "写一个计算两个数之和的 Python 函数"}],
        expected_behaviors=["contains:def", "contains:return", "no_error"]
    ),
    EvaluationCase(
        id="code-002",
        name="类生成",
        description="生成 Python 类",
        dimension=EvaluationDimension.COMPLETENESS,
        messages=[{"role": "user", "content": "写一个简单的 Python 类表示学生，包含姓名和年龄属性"}],
        expected_behaviors=["contains:class", "contains:__init__", "contains:self"]
    ),
    EvaluationCase(
        id="code-003",
        name="算法实现",
        description="实现经典算法",
        dimension=EvaluationDimension.COMPLETENESS,
        messages=[{"role": "user", "content": "用 Python 实现二分查找"}],
        expected_behaviors=["contains:def", "contains:mid", "no_error"]
    ),
    EvaluationCase(
        id="code-004",
        name="代码解释",
        description="解释代码功能",
        dimension=EvaluationDimension.ACCURACY,
        messages=[{"role": "user", "content": "解释这段代码：[x**2 for x in range(10)]"}],
        expected_behaviors=["contains:列表", "no_error"]
    ),
    EvaluationCase(
        id="code-005",
        name="错误修复建议",
        description="识别并建议修复代码错误",
        dimension=EvaluationDimension.ACCURACY,
        messages=[{"role": "user", "content": "这段代码有什么问题？def add(a, b) return a + b"}],
        expected_behaviors=["contains::", "no_error"]
    ),
]


# ==================== 4. 知识问答评估用例 ====================

KNOWLEDGE_EVALUATION_CASES = [
    EvaluationCase(
        id="know-001",
        name="技术概念解释",
        description="解释技术概念",
        dimension=EvaluationDimension.RELEVANCE,
        messages=[{"role": "user", "content": "什么是 API？"}],
        expected_behaviors=["contains:接口", "length>50", "no_error"]
    ),
    EvaluationCase(
        id="know-002",
        name="技术对比",
        description="对比两种技术",
        dimension=EvaluationDimension.COMPLETENESS,
        messages=[{"role": "user", "content": "Python 和 JavaScript 有什么区别？"}],
        expected_behaviors=["contains:python", "contains:javascript", "length>100"]
    ),
    EvaluationCase(
        id="know-003",
        name="最佳实践",
        description="提供最佳实践建议",
        dimension=EvaluationDimension.COMPLETENESS,
        messages=[{"role": "user", "content": "Python 代码有哪些最佳实践？"}],
        expected_behaviors=["length>100", "no_error"]
    ),
    EvaluationCase(
        id="know-004",
        name="工具推荐",
        description="推荐合适的工具",
        dimension=EvaluationDimension.RELEVANCE,
        messages=[{"role": "user", "content": "有什么好用的 Python IDE？"}],
        expected_behaviors=["no_error", "length>30"]
    ),
]


# ==================== 5. 边界情况评估用例 ====================

EDGE_CASE_EVALUATION_CASES = [
    EvaluationCase(
        id="edge-001",
        name="模糊问题处理",
        description="处理模糊问题",
        dimension=EvaluationDimension.ERROR_HANDLING,
        messages=[{"role": "user", "content": "嗯"}],
        expected_behaviors=["no_error", "length>5"]
    ),
    EvaluationCase(
        id="edge-002",
        name="超长输入处理",
        description="处理长输入",
        dimension=EvaluationDimension.ERROR_HANDLING,
        messages=[{"role": "user", "content": "请帮我 " + "分析这段代码 " * 50}],
        expected_behaviors=["no_error"]
    ),
    EvaluationCase(
        id="edge-003",
        name="特殊字符处理",
        description="处理特殊字符",
        dimension=EvaluationDimension.ERROR_HANDLING,
        messages=[{"role": "user", "content": "测试 <>&\"' 特殊字符"}],
        expected_behaviors=["no_error"]
    ),
    EvaluationCase(
        id="edge-004",
        name="多语言混合",
        description="处理多语言输入",
        dimension=EvaluationDimension.ERROR_HANDLING,
        messages=[{"role": "user", "content": "Hello 你好 こんにちは 안녕하세요"}],
        expected_behaviors=["no_error", "length>10"]
    ),
    EvaluationCase(
        id="edge-005",
        name="代码与自然语言混合",
        description="处理代码和自然语言混合",
        dimension=EvaluationDimension.RELEVANCE,
        messages=[{"role": "user", "content": "解释 print('hello') 这行代码"}],
        expected_behaviors=["contains:print", "no_error"]
    ),
]


# ==================== 6. 响应质量评估用例 ====================

QUALITY_EVALUATION_CASES = [
    EvaluationCase(
        id="qual-001",
        name="回答完整性",
        description="测试回答是否完整",
        dimension=EvaluationDimension.COMPLETENESS,
        messages=[{"role": "user", "content": "列出 Python 的 5 个核心特性"}],
        expected_behaviors=["length>100", "no_error"]
    ),
    EvaluationCase(
        id="qual-002",
        name="结构化回答",
        description="测试回答是否有结构",
        dimension=EvaluationDimension.COMPLETENESS,
        messages=[{"role": "user", "content": "如何学习编程？请分步骤说明"}],
        expected_behaviors=["length>150", "no_error"]
    ),
    EvaluationCase(
        id="qual-003",
        name="代码注释",
        description="测试代码是否有注释",
        dimension=EvaluationDimension.COMPLETENESS,
        messages=[{"role": "user", "content": "写一个带注释的冒泡排序算法"}],
        expected_behaviors=["contains:#", "contains:def", "no_error"]
    ),
]


# ==================== 综合评估 ====================

ALL_EVALUATION_CASES = (
    STANDARD_EVALUATION_CASES +
    INTENT_EVALUATION_CASES +
    MULTI_TURN_EVALUATION_CASES +
    CODE_EVALUATION_CASES +
    KNOWLEDGE_EVALUATION_CASES +
    EDGE_CASE_EVALUATION_CASES +
    QUALITY_EVALUATION_CASES
)


def run_comprehensive_evaluation(
    backend_url: str = "http://localhost:8000",
    categories: List[str] = None
):
    """
    运行综合评估
    
    Args:
        backend_url: 后端 URL
        categories: 要评估的类别列表，None 表示全部
                   可选: standard, intent, multi_turn, code, knowledge, edge, quality
    """
    category_map = {
        "standard": STANDARD_EVALUATION_CASES,
        "intent": INTENT_EVALUATION_CASES,
        "multi_turn": MULTI_TURN_EVALUATION_CASES,
        "code": CODE_EVALUATION_CASES,
        "knowledge": KNOWLEDGE_EVALUATION_CASES,
        "edge": EDGE_CASE_EVALUATION_CASES,
        "quality": QUALITY_EVALUATION_CASES,
    }
    
    if categories:
        cases = []
        for cat in categories:
            if cat in category_map:
                cases.extend(category_map[cat])
    else:
        cases = ALL_EVALUATION_CASES
    
    evaluator = ChatBotEvaluator(backend_url)
    
    print("=" * 70)
    print("🤖 ChatBot 综合能力评估")
    print("=" * 70)
    print(f"评估用例总数: {len(cases)}")
    print()
    
    report = evaluator.run_evaluation(cases)
    
    if "error" in report:
        print(f"❌ 评估失败: {report['error']}")
        return report
    
    # 打印详细报告
    print()
    print("=" * 70)
    print("📊 评估报告")
    print("=" * 70)
    
    print(f"\n📈 总体统计:")
    print(f"  总用例数: {report['total_cases']}")
    print(f"  通过数: {report['passed_cases']}")
    print(f"  总体得分: {report['overall_score']:.1f}/100")
    print(f"  通过率: {report['overall_pass_rate']:.1f}%")
    print(f"  平均延迟: {report['avg_latency_ms']:.0f}ms")
    
    print(f"\n📊 各维度得分:")
    for dim, scores in report['dimension_scores'].items():
        bar = "█" * int(scores['mean'] / 10) + "░" * (10 - int(scores['mean'] / 10))
        print(f"  {dim:20s}: {bar} {scores['mean']:.1f}/100 "
              f"(通过率: {scores['pass_rate']:.0f}%)")
    
    # 失败用例详情
    failed_cases = [r for r in report['results'] if not r['passed']]
    if failed_cases:
        print(f"\n❌ 失败用例 ({len(failed_cases)} 个):")
        for r in failed_cases[:5]:  # 只显示前 5 个
            print(f"  - {r['name']} (得分: {r['score']:.1f})")
    
    # 性能分析
    all_latencies = [r['latency_ms'] for r in report['results']]
    print(f"\n⏱️ 性能分析:")
    print(f"  最小延迟: {min(all_latencies):.0f}ms")
    print(f"  最大延迟: {max(all_latencies):.0f}ms")
    print(f"  P50 延迟: {sorted(all_latencies)[len(all_latencies)//2]:.0f}ms")
    print(f"  P95 延迟: {sorted(all_latencies)[int(len(all_latencies)*0.95)]:.0f}ms")
    
    # 评级
    score = report['overall_score']
    if score >= 90:
        grade = "A+ (优秀)"
    elif score >= 80:
        grade = "A (良好)"
    elif score >= 70:
        grade = "B (合格)"
    elif score >= 60:
        grade = "C (及格)"
    else:
        grade = "D (需改进)"
    
    print(f"\n🏆 综合评级: {grade}")
    print("=" * 70)
    
    return report


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ChatBot 综合评估")
    parser.add_argument("--url", default="http://localhost:8000", help="后端 URL")
    parser.add_argument("--categories", nargs="+", 
                       choices=["standard", "intent", "multi_turn", "code", 
                               "knowledge", "edge", "quality"],
                       help="要评估的类别")
    
    args = parser.parse_args()
    
    run_comprehensive_evaluation(args.url, args.categories)



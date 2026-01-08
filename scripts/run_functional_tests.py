#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
功能测试运行器

一键运行所有功能测试并生成报告。

使用方法:
    python scripts/run_functional_tests.py                    # 运行全部测试
    python scripts/run_functional_tests.py --quick            # 快速测试
    python scripts/run_functional_tests.py --category api     # 只测试 API
    python scripts/run_functional_tests.py --report           # 生成 HTML 报告
"""
import subprocess
import sys
import os
import time
import json
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_backend():
    """检查后端是否运行"""
    import requests
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        return response.status_code in [200, 503]
    except:
        return False


def run_pytest(test_files, extra_args=None):
    """运行 pytest"""
    cmd = ["python", "-m", "pytest"]
    cmd.extend(test_files)
    cmd.extend(["-v", "--tb=short"])
    
    if extra_args:
        cmd.extend(extra_args)
    
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode == 0


def run_all_functional_tests(quick=False, category=None, report=False):
    """运行所有功能测试"""
    print("=" * 70)
    print("🧪 功能测试运行器")
    print("=" * 70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 检查后端
    print("🔍 检查后端服务...")
    if not check_backend():
        print("❌ 后端服务未运行！")
        print("请先启动后端: cd backend && python run.py")
        return False
    print("✅ 后端服务正常")
    print()
    
    # 测试文件分类
    test_categories = {
        "api": [
            "tests/functional/test_all_api_endpoints.py",
        ],
        "edge": [
            "tests/functional/test_edge_cases.py",
        ],
        "performance": [
            "tests/functional/test_performance.py",
        ],
        "scenarios": [
            "tests/functional/test_chat_scenarios.py",
        ],
    }
    
    # 确定要运行的测试
    if category:
        if category not in test_categories:
            print(f"❌ 未知类别: {category}")
            print(f"可用类别: {list(test_categories.keys())}")
            return False
        test_files = test_categories[category]
    else:
        test_files = []
        for files in test_categories.values():
            test_files.extend(files)
    
    # 过滤存在的文件
    existing_files = [f for f in test_files if (PROJECT_ROOT / f).exists()]
    
    if not existing_files:
        print("❌ 没有找到测试文件")
        return False
    
    print(f"📋 将运行 {len(existing_files)} 个测试文件:")
    for f in existing_files:
        print(f"   - {f}")
    print()
    
    # 额外参数
    extra_args = []
    if quick:
        extra_args.extend(["-x", "--timeout=30"])  # 失败即停，30秒超时
    
    if report:
        report_dir = PROJECT_ROOT / "test_reports"
        report_dir.mkdir(exist_ok=True)
        report_file = report_dir / f"functional_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        extra_args.extend([f"--html={report_file}", "--self-contained-html"])
    
    # 运行测试
    print("🚀 开始运行测试...")
    print("-" * 70)
    
    start_time = time.time()
    success = run_pytest(existing_files, extra_args)
    elapsed = time.time() - start_time
    
    print("-" * 70)
    print()
    
    if success:
        print(f"✅ 所有测试通过! (耗时: {elapsed:.1f}s)")
    else:
        print(f"❌ 部分测试失败 (耗时: {elapsed:.1f}s)")
    
    if report:
        print(f"📄 测试报告: {report_file}")
    
    return success


def run_evaluation(categories=None):
    """运行评估测试"""
    print("=" * 70)
    print("📊 能力评估运行器")
    print("=" * 70)
    
    # 检查后端
    if not check_backend():
        print("❌ 后端服务未运行！")
        return False
    
    # 运行综合评估
    cmd = ["python", "-m", "tests.evaluation.comprehensive_evaluation"]
    if categories:
        cmd.extend(["--categories"] + categories)
    
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode == 0


def print_summary():
    """打印测试覆盖摘要"""
    print()
    print("=" * 70)
    print("📋 功能测试覆盖摘要")
    print("=" * 70)
    print("""
测试文件:
  1. test_all_api_endpoints.py - 完整 API 端点测试
     - Chat API (10 个端点)
     - Documents API (4 个端点)
     - Settings API (10 个端点)
     - Tools API (5 个端点)
     - Batch API (2 个端点)
     - 场景测试 (多轮对话、文档工作流、设置工作流)

  2. test_edge_cases.py - 边界条件测试
     - 输入边界 (空、超长、Unicode、特殊字符)
     - 会话管理边界
     - API 请求格式
     - 并发测试
     - 安全性测试 (SQL 注入、XSS、路径遍历)
     - 超时和重试
     - 意图分析边界
     - 文档操作边界

  3. test_performance.py - 性能测试
     - 端点性能基准
     - 吞吐量测试
     - 延迟稳定性测试
     - 资源敏感性测试
     - 流式响应性能

  4. test_chat_scenarios.py - 对话场景测试
     - 基础对话
     - 多轮对话
     - 意图识别
     - 工具调用
     - 文档管理
     - 技能系统
     - 错误处理
     - 流式响应
     - 批量操作

评估框架:
  - chatbot_evaluation.py - 标准评估 (9 个用例)
  - comprehensive_evaluation.py - 综合评估 (35+ 个用例)
    - 意图识别评估
    - 多轮对话评估
    - 代码能力评估
    - 知识问答评估
    - 边界情况评估
    - 响应质量评估
""")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="功能测试运行器")
    parser.add_argument("--quick", action="store_true", help="快速测试模式")
    parser.add_argument("--category", choices=["api", "edge", "performance", "scenarios"],
                       help="只运行特定类别的测试")
    parser.add_argument("--report", action="store_true", help="生成 HTML 报告")
    parser.add_argument("--evaluate", action="store_true", help="运行能力评估")
    parser.add_argument("--eval-categories", nargs="+",
                       choices=["standard", "intent", "multi_turn", "code", 
                               "knowledge", "edge", "quality"],
                       help="评估类别")
    parser.add_argument("--summary", action="store_true", help="显示测试覆盖摘要")
    
    args = parser.parse_args()
    
    if args.summary:
        print_summary()
        sys.exit(0)
    
    if args.evaluate:
        success = run_evaluation(args.eval_categories)
    else:
        success = run_all_functional_tests(
            quick=args.quick,
            category=args.category,
            report=args.report
        )
    
    sys.exit(0 if success else 1)



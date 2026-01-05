#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Agentic ChatBot 测试总入口

用法:
    python run_tests.py                    # 显示帮助
    python run_tests.py all                # 运行所有测试
    python run_tests.py unit               # 单元测试
    python run_tests.py regression         # 回归测试
    python run_tests.py benchmark          # 性能基准
    python run_tests.py eval               # 能力评估
    python run_tests.py quick              # 快速冒烟测试
"""
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent


def run_command(cmd: str, description: str) -> int:
    """运行命令并返回退出码"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"$ {cmd}\n")
    
    result = subprocess.run(cmd, shell=True, cwd=PROJECT_ROOT)
    return result.returncode


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("可用命令:")
        print("  all        - 运行所有测试（不含基准测试）")
        print("  unit       - 单元测试")
        print("  integration- 集成测试")
        print("  regression - 回归测试（P0 级别）")
        print("  regression-all - 全部回归测试")
        print("  benchmark  - 性能基准测试")
        print("  eval       - 能力评估")
        print("  quick      - 快速冒烟测试（5 个核心用例）")
        print("  coverage   - 带覆盖率的测试")
        return 0
        
    command = sys.argv[1].lower()
    
    # 激活虚拟环境的前缀
    venv_activate = "source backend/venv/bin/activate && "
    
    if command == "all":
        # 运行所有测试（不含基准测试，因为耗时较长）
        return run_command(
            f"{venv_activate}python -m pytest tests/ -v --ignore=tests/benchmark/",
            "运行所有测试"
        )
        
    elif command == "unit":
        return run_command(
            f"{venv_activate}python -m pytest tests/unit/ -v",
            "单元测试"
        )
        
    elif command == "integration":
        return run_command(
            f"{venv_activate}python -m pytest tests/integration/ -v",
            "集成测试"
        )
        
    elif command == "regression":
        return run_command(
            f"{venv_activate}python -m pytest tests/regression/test_regression.py -v -k 'P0'",
            "P0 回归测试"
        )
        
    elif command == "regression-all":
        return run_command(
            f"{venv_activate}python tests/regression/test_regression.py",
            "全部回归测试"
        )
        
    elif command == "benchmark":
        return run_command(
            f"{venv_activate}python tests/benchmark/test_performance.py",
            "性能基准测试"
        )
        
    elif command == "eval":
        return run_command(
            f"{venv_activate}python -m tests.evaluation.eval_framework",
            "能力评估"
        )
        
    elif command == "quick":
        # 快速冒烟测试
        return run_command(
            f"{venv_activate}python tests/test_sdk_comprehensive.py --quick",
            "快速冒烟测试"
        )
        
    elif command == "coverage":
        return run_command(
            f"{venv_activate}python -m pytest tests/ --cov=backend/app --cov-report=html --cov-report=term-missing",
            "覆盖率测试"
        )
        
    else:
        print(f"❌ 未知命令: {command}")
        print("运行 'python run_tests.py' 查看帮助")
        return 1


if __name__ == "__main__":
    sys.exit(main())


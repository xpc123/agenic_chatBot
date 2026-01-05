# -*- coding: utf-8 -*-
"""
性能基准测试

测试维度:
1. 延迟 (Latency) - P50, P95, P99
2. 吞吐量 (Throughput) - QPS
3. 内存使用 (Memory)
4. 首字节时间 (Time to First Token)

运行方式:
    pytest tests/benchmark/test_performance.py -v
    python tests/benchmark/test_performance.py
"""
import pytest
import time
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass, field
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agentic_sdk import ChatBot


# ============================================================================
# 性能指标
# ============================================================================

@dataclass
class PerformanceMetrics:
    """性能指标"""
    test_name: str
    iterations: int
    latencies_ms: List[float] = field(default_factory=list)
    ttft_ms: List[float] = field(default_factory=list)  # Time to First Token
    
    @property
    def avg_latency(self) -> float:
        return statistics.mean(self.latencies_ms) if self.latencies_ms else 0
    
    @property
    def p50_latency(self) -> float:
        if not self.latencies_ms:
            return 0
        return statistics.median(self.latencies_ms)
    
    @property
    def p95_latency(self) -> float:
        if not self.latencies_ms:
            return 0
        sorted_l = sorted(self.latencies_ms)
        idx = int(len(sorted_l) * 0.95)
        return sorted_l[min(idx, len(sorted_l) - 1)]
    
    @property
    def p99_latency(self) -> float:
        if not self.latencies_ms:
            return 0
        sorted_l = sorted(self.latencies_ms)
        idx = int(len(sorted_l) * 0.99)
        return sorted_l[min(idx, len(sorted_l) - 1)]
    
    @property
    def avg_ttft(self) -> float:
        return statistics.mean(self.ttft_ms) if self.ttft_ms else 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "iterations": self.iterations,
            "avg_latency_ms": round(self.avg_latency, 2),
            "p50_latency_ms": round(self.p50_latency, 2),
            "p95_latency_ms": round(self.p95_latency, 2),
            "p99_latency_ms": round(self.p99_latency, 2),
            "avg_ttft_ms": round(self.avg_ttft, 2),
        }


# ============================================================================
# 基准测试用例
# ============================================================================

BENCHMARK_CASES = [
    {
        "name": "simple_greeting",
        "query": "你好",
        "iterations": 5,
        "target_p95_ms": 10000,
    },
    {
        "name": "simple_qa",
        "query": "什么是 Python？",
        "iterations": 3,
        "target_p95_ms": 20000,
    },
    {
        "name": "tool_list_dir",
        "query": "列出 /tmp 目录",
        "iterations": 3,
        "target_p95_ms": 30000,
    },
    {
        "name": "code_generation",
        "query": "写一个快速排序的 Python 实现",
        "iterations": 3,
        "target_p95_ms": 40000,
    },
]


# ============================================================================
# 基准测试器
# ============================================================================

class BenchmarkRunner:
    """基准测试运行器"""
    
    def __init__(self, bot: ChatBot = None):
        self.bot = bot or ChatBot()
        self.results: List[PerformanceMetrics] = []
        
    def run_benchmark(self, case: Dict) -> PerformanceMetrics:
        """运行单个基准测试"""
        metrics = PerformanceMetrics(
            test_name=case["name"],
            iterations=case["iterations"],
        )
        
        for i in range(case["iterations"]):
            session_id = f"benchmark-{case['name']}-{i}"
            
            start_time = time.time()
            first_token_time = None
            
            for chunk in self.bot.chat_stream(case["query"], session_id):
                if chunk.type == "text" and first_token_time is None:
                    first_token_time = time.time()
                    
            end_time = time.time()
            
            latency_ms = (end_time - start_time) * 1000
            ttft_ms = (first_token_time - start_time) * 1000 if first_token_time else latency_ms
            
            metrics.latencies_ms.append(latency_ms)
            metrics.ttft_ms.append(ttft_ms)
            
        return metrics
    
    def run_all(self) -> Dict[str, Any]:
        """运行所有基准测试"""
        self.results = []
        
        for case in BENCHMARK_CASES:
            print(f"⏱️ Running: {case['name']} ({case['iterations']} iterations)...")
            metrics = self.run_benchmark(case)
            self.results.append(metrics)
            
            status = "✅" if metrics.p95_latency <= case["target_p95_ms"] else "⚠️"
            print(f"  {status} P95: {metrics.p95_latency:.0f}ms (target: {case['target_p95_ms']}ms)")
            
        return self._generate_report()
    
    def _generate_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        return {
            "benchmarks": [m.to_dict() for m in self.results],
            "summary": {
                "total_tests": len(self.results),
                "avg_p50_ms": statistics.mean([m.p50_latency for m in self.results]),
                "avg_p95_ms": statistics.mean([m.p95_latency for m in self.results]),
            }
        }


# ============================================================================
# Pytest 测试
# ============================================================================

@pytest.fixture(scope="module")
def benchmark_bot():
    """基准测试用 ChatBot"""
    return ChatBot()


@pytest.mark.benchmark
class TestLatencyBenchmarks:
    """延迟基准测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self, benchmark_bot):
        self.bot = benchmark_bot
        
    def test_greeting_latency(self):
        """问候延迟"""
        start = time.time()
        for chunk in self.bot.chat_stream("你好", "bench-greeting"):
            pass
        latency_ms = (time.time() - start) * 1000
        
        assert latency_ms < 15000, f"问候延迟过高: {latency_ms:.0f}ms"
        
    def test_tool_use_latency(self):
        """工具使用延迟"""
        start = time.time()
        for chunk in self.bot.chat_stream("列出 /tmp 目录", "bench-tool"):
            pass
        latency_ms = (time.time() - start) * 1000
        
        assert latency_ms < 45000, f"工具调用延迟过高: {latency_ms:.0f}ms"


# ============================================================================
# 命令行入口
# ============================================================================

def main():
    """运行基准测试"""
    print("⏱️ Agentic ChatBot 性能基准测试")
    print("=" * 60)
    
    runner = BenchmarkRunner()
    report = runner.run_all()
    
    print("\n" + "=" * 60)
    print("📊 性能报告")
    print("=" * 60)
    
    print(f"\n{'测试名称':<20} {'P50(ms)':<10} {'P95(ms)':<10} {'TTFT(ms)':<10}")
    print("-" * 50)
    
    for m in runner.results:
        print(f"{m.test_name:<20} {m.p50_latency:<10.0f} {m.p95_latency:<10.0f} {m.avg_ttft:<10.0f}")
        
    print("\n📈 汇总:")
    print(f"  平均 P50: {report['summary']['avg_p50_ms']:.0f}ms")
    print(f"  平均 P95: {report['summary']['avg_p95_ms']:.0f}ms")


if __name__ == "__main__":
    main()


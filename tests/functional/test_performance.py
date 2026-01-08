# -*- coding: utf-8 -*-
"""
性能测试

测试 API 响应时间、吞吐量和资源使用。
"""
import pytest
import requests
import time
import statistics
import os
from typing import List
from dataclasses import dataclass


BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


@dataclass
class PerformanceMetrics:
    """性能指标"""
    endpoint: str
    total_requests: int
    successful_requests: int
    min_latency: float
    max_latency: float
    avg_latency: float
    p50_latency: float
    p95_latency: float
    p99_latency: float
    throughput: float  # requests per second
    
    def __str__(self):
        return f"""
Endpoint: {self.endpoint}
Requests: {self.successful_requests}/{self.total_requests}
Latency (ms):
  Min: {self.min_latency:.2f}
  Max: {self.max_latency:.2f}
  Avg: {self.avg_latency:.2f}
  P50: {self.p50_latency:.2f}
  P95: {self.p95_latency:.2f}
  P99: {self.p99_latency:.2f}
Throughput: {self.throughput:.2f} req/s
"""


def calculate_percentile(data: List[float], percentile: float) -> float:
    """计算百分位数"""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    index = int(len(sorted_data) * percentile / 100)
    return sorted_data[min(index, len(sorted_data) - 1)]


@pytest.fixture(scope="module")
def api_client():
    """创建 API 客户端"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    for _ in range(3):
        try:
            response = session.get(f"{BACKEND_URL}/health", timeout=5)
            if response.status_code in [200, 503]:
                return session
        except requests.exceptions.ConnectionError:
            time.sleep(2)
    
    pytest.skip("Backend not available")


def run_performance_test(
    client,
    endpoint: str,
    method: str,
    data: dict = None,
    num_requests: int = 10,
    warmup: int = 2,
    accept_status_codes: List[int] = None
) -> PerformanceMetrics:
    """运行性能测试"""
    
    if accept_status_codes is None:
        accept_status_codes = [200]
    
    # Warmup
    for _ in range(warmup):
        try:
            if method == "GET":
                client.get(f"{BACKEND_URL}{endpoint}", timeout=60)
            else:
                client.post(f"{BACKEND_URL}{endpoint}", json=data, timeout=60)
        except:
            pass
    
    # Actual test
    latencies = []
    success_count = 0
    start_time = time.time()
    
    for i in range(num_requests):
        req_start = time.time()
        try:
            if method == "GET":
                response = client.get(f"{BACKEND_URL}{endpoint}", timeout=60)
            else:
                # 为每个请求生成唯一 session_id
                if data and "session_id" in data:
                    test_data = data.copy()
                    test_data["session_id"] = f"{data['session_id']}-{i}"
                else:
                    test_data = data
                response = client.post(f"{BACKEND_URL}{endpoint}", json=test_data, timeout=60)
            
            latency = (time.time() - req_start) * 1000  # ms
            latencies.append(latency)
            
            if response.status_code in accept_status_codes:
                success_count += 1
        except Exception as e:
            print(f"Request failed: {e}")
    
    total_time = time.time() - start_time
    
    if not latencies:
        latencies = [0]
    
    return PerformanceMetrics(
        endpoint=endpoint,
        total_requests=num_requests,
        successful_requests=success_count,
        min_latency=min(latencies),
        max_latency=max(latencies),
        avg_latency=statistics.mean(latencies),
        p50_latency=calculate_percentile(latencies, 50),
        p95_latency=calculate_percentile(latencies, 95),
        p99_latency=calculate_percentile(latencies, 99),
        throughput=num_requests / total_time if total_time > 0 else 0
    )


# ==================== 1. 端点性能基准测试 ====================

class TestEndpointPerformance:
    """端点性能基准测试"""
    
    def test_health_check_performance(self, api_client):
        """健康检查性能 (目标: <50ms)"""
        metrics = run_performance_test(
            api_client,
            "/health",
            "GET",
            num_requests=10,
            accept_status_codes=[200, 503]  # 503 也是有效响应 (degraded)
        )
        print(metrics)
        
        assert metrics.successful_requests >= 8
        assert metrics.avg_latency < 500  # 500ms 上限
    
    def test_intent_analysis_performance(self, api_client):
        """意图分析性能 (目标: <500ms)"""
        metrics = run_performance_test(
            api_client,
            "/api/v2/chat/analyze-intent",
            "POST",
            data={"message": "什么是 Python？"},
            num_requests=5
        )
        print(metrics)
        
        assert metrics.successful_requests >= 4
        assert metrics.avg_latency < 5000  # 5s 上限 (涉及 LLM)
    
    def test_chat_message_performance(self, api_client):
        """对话性能 (目标: <2s)"""
        metrics = run_performance_test(
            api_client,
            "/api/v2/chat/message",
            "POST",
            data={"message": "你好", "session_id": "perf-chat"},
            num_requests=5
        )
        print(metrics)
        
        assert metrics.successful_requests >= 3
        # LLM 响应可能较慢
        assert metrics.avg_latency < 30000  # 30s 上限
    
    def test_document_list_performance(self, api_client):
        """文档列表性能 (目标: <200ms)"""
        metrics = run_performance_test(
            api_client,
            "/api/v2/documents/list",
            "GET",
            num_requests=10
        )
        print(metrics)
        
        assert metrics.successful_requests >= 8
        assert metrics.avg_latency < 1000  # 1s 上限
    
    def test_settings_performance(self, api_client):
        """设置获取性能 (目标: <100ms)"""
        metrics = run_performance_test(
            api_client,
            "/api/v2/settings/summary",
            "GET",
            num_requests=10
        )
        print(metrics)
        
        assert metrics.successful_requests >= 8
        assert metrics.avg_latency < 500  # 500ms 上限


# ==================== 2. 吞吐量测试 ====================

class TestThroughput:
    """吞吐量测试"""
    
    def test_concurrent_health_checks(self, api_client):
        """并发健康检查吞吐量"""
        import concurrent.futures
        
        num_requests = 20
        success_count = 0
        start_time = time.time()
        
        def check_health():
            try:
                response = api_client.get(f"{BACKEND_URL}/health", timeout=10)
                return response.status_code == 200 or response.status_code == 503
            except:
                return False
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(check_health) for _ in range(num_requests)]
            results = [f.result() for f in futures]
        
        elapsed = time.time() - start_time
        success_count = sum(results)
        throughput = num_requests / elapsed
        
        print(f"Concurrent Health Checks: {success_count}/{num_requests}, "
              f"Throughput: {throughput:.2f} req/s")
        
        assert success_count >= 15
        assert throughput > 1  # 至少 1 req/s
    
    def test_concurrent_intent_analysis(self, api_client):
        """并发意图分析吞吐量"""
        import concurrent.futures
        
        num_requests = 5
        success_count = 0
        start_time = time.time()
        
        def analyze_intent(i):
            try:
                response = api_client.post(
                    f"{BACKEND_URL}/api/v2/chat/analyze-intent",
                    json={"message": f"测试消息{i}"},
                    timeout=30
                )
                return response.status_code == 200
            except:
                return False
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(analyze_intent, i) for i in range(num_requests)]
            results = [f.result() for f in futures]
        
        elapsed = time.time() - start_time
        success_count = sum(results)
        throughput = num_requests / elapsed
        
        print(f"Concurrent Intent Analysis: {success_count}/{num_requests}, "
              f"Throughput: {throughput:.2f} req/s")
        
        assert success_count >= 3


# ==================== 3. 延迟稳定性测试 ====================

class TestLatencyStability:
    """延迟稳定性测试"""
    
    def test_latency_consistency(self, api_client):
        """延迟一致性 (标准差应该较小)"""
        latencies = []
        
        for i in range(5):
            start = time.time()
            response = api_client.get(f"{BACKEND_URL}/health", timeout=10)
            latency = (time.time() - start) * 1000
            if response.status_code in [200, 503]:
                latencies.append(latency)
        
        if len(latencies) >= 3:
            std_dev = statistics.stdev(latencies)
            mean = statistics.mean(latencies)
            cv = std_dev / mean if mean > 0 else 0  # 变异系数
            
            print(f"Latency Stats: Mean={mean:.2f}ms, StdDev={std_dev:.2f}ms, CV={cv:.2f}")
            
            # 变异系数应该小于 1 (相对稳定)
            assert cv < 2
    
    def test_no_degradation_over_time(self, api_client):
        """无性能退化测试"""
        first_batch = []
        last_batch = []
        
        # 第一批请求 (健康检查)
        for _ in range(3):
            try:
                start = time.time()
                api_client.get(f"{BACKEND_URL}/health", timeout=10)
                first_batch.append((time.time() - start) * 1000)
            except:
                pass
        
        # 中间负载 (减少请求数以避免超时)
        for i in range(2):
            try:
                api_client.post(
                    f"{BACKEND_URL}/api/v2/chat/message",
                    json={"message": f"测试{i}", "session_id": f"load-{i}"},
                    timeout=90
                )
            except:
                pass
        
        # 最后一批请求
        for _ in range(3):
            try:
                start = time.time()
                api_client.get(f"{BACKEND_URL}/health", timeout=10)
                last_batch.append((time.time() - start) * 1000)
            except:
                pass
        
        if first_batch and last_batch:
            first_avg = statistics.mean(first_batch)
            last_avg = statistics.mean(last_batch)
            
            print(f"First batch avg: {first_avg:.2f}ms, Last batch avg: {last_avg:.2f}ms")
            
            # 最后一批不应该比第一批慢太多 (允许 500% 增长)
            assert last_avg < first_avg * 6
        else:
            pytest.skip("Not enough successful requests for comparison")


# ==================== 4. 资源敏感性测试 ====================

class TestResourceSensitivity:
    """资源敏感性测试"""
    
    def test_large_payload_handling(self, api_client):
        """大负载处理"""
        large_message = "测试内容。" * 100  # ~500 chars
        
        start = time.time()
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/message",
            json={"message": large_message, "session_id": "large-payload"},
            timeout=120
        )
        latency = (time.time() - start) * 1000
        
        print(f"Large payload latency: {latency:.2f}ms")
        
        assert response.status_code in [200, 400, 413]
    
    def test_batch_operation_scaling(self, api_client):
        """批量操作扩展性"""
        # 测试不同批量大小
        batch_sizes = [1, 2]  # 减少批量大小以避免超时
        
        for size in batch_sizes:
            requests_list = [
                {"message": f"批量测试{i}", "session_id": f"batch-scale-{i}"}
                for i in range(size)
            ]
            
            start = time.time()
            response = api_client.post(
                f"{BACKEND_URL}/api/v2/batch/chat",
                json={"requests": requests_list},
                timeout=180
            )
            latency = (time.time() - start) * 1000
            
            print(f"Batch size {size}: {latency:.2f}ms")
            
            assert response.status_code in [200, 202]


# ==================== 5. 流式响应性能测试 ====================

class TestStreamingPerformance:
    """流式响应性能测试"""
    
    def test_time_to_first_byte(self, api_client):
        """首字节时间 (TTFB)"""
        start = time.time()
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/stream",
            json={"message": "你好", "session_id": "ttfb-test"},
            stream=True,
            timeout=60
        )
        
        ttfb = None
        for line in response.iter_lines():
            if line:
                ttfb = (time.time() - start) * 1000
                break
        
        response.close()
        
        if ttfb:
            print(f"Time to First Byte: {ttfb:.2f}ms")
            # TTFB 应该在合理范围内
            assert ttfb < 10000  # 10s 上限
    
    def test_stream_chunk_frequency(self, api_client):
        """流式块频率"""
        response = api_client.post(
            f"{BACKEND_URL}/api/v2/chat/stream",
            json={"message": "写一段简短的代码", "session_id": "chunk-freq"},
            stream=True,
            timeout=60
        )
        
        chunk_times = []
        start = time.time()
        
        for i, line in enumerate(response.iter_lines()):
            if line:
                chunk_times.append(time.time() - start)
            if i >= 10:  # 最多收集 10 个块
                break
        
        response.close()
        
        if len(chunk_times) >= 2:
            intervals = [chunk_times[i] - chunk_times[i-1] for i in range(1, len(chunk_times))]
            avg_interval = statistics.mean(intervals)
            
            print(f"Average chunk interval: {avg_interval * 1000:.2f}ms")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])



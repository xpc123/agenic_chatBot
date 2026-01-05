# 🧪 Agentic ChatBot 测试评估体系

## 📊 测试金字塔

```
                    ┌─────────────────┐
                    │   E2E Tests     │  ← 端到端场景测试
                    │    (10%)        │
                    ├─────────────────┤
                    │  Integration    │  ← SDK 集成测试
                    │    (30%)        │
                    ├─────────────────┤
                    │   Unit Tests    │  ← 组件单元测试
                    │    (60%)        │
                    └─────────────────┘
```

## 📁 目录结构

```
tests/
├── README.md                    # 本文档
├── conftest.py                  # Pytest 配置和 fixtures
├── pytest.ini                   # Pytest 配置
│
├── unit/                        # 单元测试 (60%)
│   ├── test_intent_recognizer.py
│   ├── test_tool_orchestrator.py
│   ├── test_context_manager.py
│   ├── test_memory_manager.py
│   └── test_llm_client.py
│
├── integration/                 # 集成测试 (30%)
│   ├── test_sdk_api.py          # SDK 公开 API
│   ├── test_tool_execution.py   # 工具执行
│   ├── test_rag_pipeline.py     # RAG 流程
│   └── test_conversation_flow.py # 对话流程
│
├── e2e/                         # 端到端测试 (10%)
│   ├── test_user_scenarios.py   # 用户场景
│   └── test_multi_turn.py       # 多轮对话
│
├── regression/                  # 回归测试套件
│   ├── golden_cases.json        # 黄金用例（期望输出）
│   ├── test_regression.py       # 回归测试执行
│   └── snapshots/               # 响应快照
│
├── benchmark/                   # 性能基准测试
│   ├── test_latency.py          # 延迟测试
│   ├── test_throughput.py       # 吞吐量测试
│   └── test_memory_usage.py     # 内存使用
│
├── evaluation/                  # 能力评估
│   ├── eval_framework.py        # 评估框架
│   ├── eval_cases.yaml          # 评估用例
│   └── reports/                 # 评估报告
│
└── fixtures/                    # 测试数据
    ├── sample_files/
    ├── mock_responses/
    └── test_contexts/
```

## 🚀 快速开始

```bash
# 运行所有测试
pytest tests/ -v

# 只运行单元测试
pytest tests/unit/ -v

# 运行回归测试
pytest tests/regression/ -v

# 运行能力评估
python -m tests.evaluation.eval_framework

# 生成覆盖率报告
pytest tests/ --cov=backend/app --cov-report=html
```

## 📋 测试类型说明

### 1. 单元测试 (Unit Tests)
- 测试单个组件的功能
- 使用 Mock 隔离依赖
- 快速执行（< 1s/test）

### 2. 集成测试 (Integration Tests)
- 测试组件间的交互
- 使用真实的 LLM（或 Mock）
- 中等执行时间（1-10s/test）

### 3. 端到端测试 (E2E Tests)
- 模拟真实用户场景
- 完整的对话流程
- 较长执行时间（10-60s/test）

### 4. 回归测试 (Regression Tests)
- 黄金用例对比
- 防止功能退化
- 每次提交必须通过

### 5. 能力评估 (Capability Evaluation)
- 对标 Cursor/Copilot
- 多维度评分
- 定期执行（每周/每版本）

## 📊 评估指标

| 指标 | 说明 | 目标 | 当前得分 |
|------|------|------|----------|
| Tool Use Accuracy | 工具调用准确性 | ≥ 95% | **100%** ✅ |
| Response Relevancy | 响应相关性 | ≥ 90% | **90.8%** ✅ |
| Context Utilization | 上下文利用率 | ≥ 85% | 评估中 |
| Task Completion | 任务完成率 | ≥ 90% | **100%** ✅ |
| Latency P50 | 50分位延迟 | ≤ 5s | ~6s ⚠️ |
| Latency P95 | 95分位延迟 | ≤ 15s | ~18s ⚠️ |
| Error Rate | 错误率 | ≤ 1% | **0%** ✅ |

## 🏆 当前测试结果 (2025-01-05)

### 综合测试 (26 用例)
```
conversation:   3/3  ✅  对话功能
qa:             3/3  ✅  问答能力
file_operation: 4/4  ✅  文件操作
system:         3/3  ✅  系统操作
memory:         2/2  ✅  上下文记忆
code_analysis:  2/2  ✅  代码分析
complex_task:   1/1  ✅  复杂任务
error_handling: 2/2  ✅  错误处理
edge_case:      3/3  ✅  边界情况
cursor_like:    3/3  ✅  对标Cursor
```

### 回归测试 (10 黄金用例)
- 通过率: **100%** (10/10)

### 能力评估 (10 用例)
- 通过率: **90%** (9/10)

## 🔄 CI/CD 集成

```yaml
# .github/workflows/test.yml
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Unit Tests
        run: pytest tests/unit/ -v
        
      - name: Integration Tests
        run: pytest tests/integration/ -v
        
      - name: Regression Tests
        run: pytest tests/regression/ -v
        
      - name: Capability Evaluation
        run: python -m tests.evaluation.eval_framework -o report.json
```


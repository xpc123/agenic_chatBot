# 🧪 Agentic ChatBot 测试体系

## 📊 测试金字塔

```
                    ┌─────────────────┐
                    │   E2E Tests     │  ← 端到端场景测试 (34 tests)
                    │    (10%)        │
                    ├─────────────────┤
                    │  Functional     │  ← 功能/API 测试 (88 tests)
                    │    (25%)        │
                    ├─────────────────┤
                    │  Integration    │  ← 集成测试 (126 tests)
                    │    (35%)        │
                    ├─────────────────┤
                    │   Unit Tests    │  ← 单元测试 (82 tests)
                    │    (25%)        │
                    └─────────────────┘
```

**总计: 335+ 测试用例**

## 📁 目录结构

```
tests/
├── README.md                    # 本文档
├── conftest.py                  # Pytest 配置和全局 fixtures
├── run_tests.sh                 # 测试运行脚本
│
├── unit/                        # 🔬 单元测试 (82 tests)
│   ├── test_intent_recognizer.py    意图识别器测试
│   ├── test_memory_manager.py       记忆管理器测试
│   ├── test_orchestrator.py         编排器测试
│   ├── test_tool_executor.py        工具执行器测试
│   ├── test_skills_manager.py       技能管理器测试
│   └── test_single.py               单项测试
│
├── integration/                 # 🔗 集成测试 (126 tests)
│   ├── test_sdk_client.py           SDK 客户端测试
│   ├── test_api_v2.py               API v2 端点测试
│   ├── test_auth.py                 认证中间件测试
│   ├── test_rag.py                  RAG 系统测试
│   ├── test_mcp.py                  MCP 协议测试
│   ├── test_phase3_4.py             阶段集成测试
│   └── test_sdk_comprehensive.py    SDK 综合测试
│
├── e2e/                         # 🎯 端到端测试 (34 tests)
│   ├── test_e2e_integration.py      完整集成测试
│   └── test_chat_scenarios.py       对话场景测试
│
├── functional/                  # ⚡ 功能测试 (88 tests)
│   ├── test_all_api_endpoints.py    完整 API 端点覆盖 (46 tests)
│   ├── test_edge_cases.py           边界条件测试 (29 tests)
│   └── test_performance.py          性能测试 (13 tests)
│
├── evaluation/                  # 📊 能力评估框架
│   ├── eval_framework.py            评估框架核心
│   ├── chatbot_evaluation.py        标准评估 (9 用例)
│   └── comprehensive_evaluation.py  综合评估 (35+ 用例)
│
├── regression/                  # 🔄 回归测试 (5 tests)
│   └── test_regression.py           回归用例
│
└── fixtures/                    # 📦 测试数据
    ├── sample_files/
    └── mock_responses/
```

## 🚀 快速开始

```bash
# 运行所有测试
pytest tests/ -v

# 按类型运行
pytest tests/unit/ -v          # 单元测试
pytest tests/integration/ -v   # 集成测试
pytest tests/e2e/ -v           # 端到端测试
pytest tests/functional/ -v    # 功能测试

# 快速测试 (失败即停)
pytest tests/ -x --timeout=30

# 运行能力评估
python -m tests.evaluation.comprehensive_evaluation

# 使用测试运行器
python scripts/run_functional_tests.py --summary
python scripts/run_functional_tests.py --evaluate

# 生成覆盖率报告
pytest tests/ --cov=backend/app --cov-report=html
```

## 📋 测试类型说明

### 1. 单元测试 (Unit Tests) - 82 tests
- **目的**: 测试单个组件的功能
- **特点**: 使用 Mock 隔离依赖
- **执行时间**: < 1s/test
- **文件**: `tests/unit/`

### 2. 集成测试 (Integration Tests) - 126 tests
- **目的**: 测试组件间的交互
- **特点**: 使用 TestClient 模拟 HTTP
- **执行时间**: 1-10s/test
- **文件**: `tests/integration/`

### 3. 功能测试 (Functional Tests) - 88 tests
- **目的**: 验证 API 端点和功能
- **特点**: 覆盖所有 API 端点、边界条件、性能
- **执行时间**: 1-30s/test
- **文件**: `tests/functional/`

### 4. 端到端测试 (E2E Tests) - 34 tests
- **目的**: 模拟真实用户场景
- **特点**: 完整的对话流程
- **执行时间**: 10-60s/test
- **文件**: `tests/e2e/`

### 5. 回归测试 (Regression Tests) - 5 tests
- **目的**: 防止功能退化
- **特点**: 黄金用例对比
- **文件**: `tests/regression/`

### 6. 能力评估 (Capability Evaluation) - 44+ 用例
- **目的**: 评估 ChatBot 能力
- **维度**: 相关性、准确性、完整性、上下文、工具、延迟、错误处理
- **文件**: `tests/evaluation/`

## 📊 测试覆盖

| 模块 | 测试文件 | 用例数 | 覆盖范围 |
|------|----------|--------|----------|
| 意图识别 | unit/test_intent_recognizer.py | 14 | 意图分类、实体提取 |
| 记忆管理 | unit/test_memory_manager.py | 14 | 短期/长期记忆 |
| 编排器 | unit/test_orchestrator.py | 12 | ReAct 循环、任务编排 |
| 工具执行 | unit/test_tool_executor.py | 23 | 工具调用、错误处理 |
| 技能系统 | unit/test_skills_manager.py | 18 | 技能加载、触发 |
| SDK 客户端 | integration/test_sdk_client.py | 31 | HTTP 客户端、认证 |
| API v2 | integration/test_api_v2.py | 22 | REST API 端点 |
| 认证 | integration/test_auth.py | 17 | API Key、JWT、HMAC |
| RAG | integration/test_rag.py | 20 | 文档处理、检索 |
| MCP | integration/test_mcp.py | 18 | 协议集成、工具发现 |
| API 功能 | functional/test_all_api_endpoints.py | 46 | 全部 31 个端点 |
| 边界条件 | functional/test_edge_cases.py | 29 | 输入边界、安全性 |
| 性能 | functional/test_performance.py | 13 | 延迟、吞吐量 |
| E2E | e2e/test_e2e_integration.py | 22 | 完整场景 |
| 对话 | e2e/test_chat_scenarios.py | 12 | 多轮对话 |

## 🏆 评估指标

| 指标 | 说明 | 目标 | 状态 |
|------|------|------|------|
| API 覆盖率 | API 端点测试覆盖 | 100% | ✅ 100% |
| 工具调用准确性 | 正确调用工具 | ≥ 95% | ✅ |
| 响应相关性 | 回答与问题相关 | ≥ 90% | ✅ |
| 上下文保持 | 多轮对话记忆 | ≥ 85% | ✅ |
| 边界条件处理 | 异常输入处理 | 100% | ✅ |
| P50 延迟 | 50分位延迟 | ≤ 5s | ⚠️ ~6s |
| P95 延迟 | 95分位延迟 | ≤ 15s | ⚠️ ~18s |
| 错误率 | API 错误率 | ≤ 1% | ✅ 0% |

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
        
      - name: Functional Tests
        run: pytest tests/functional/ -v
        
      - name: Regression Tests
        run: pytest tests/regression/ -v
        
      - name: Capability Evaluation
        run: python -m tests.evaluation.comprehensive_evaluation
```

## 📅 更新日志

- **2026-01-08**: 重组测试目录结构，新增功能测试 (88 tests)
- **2026-01-08**: 新增综合评估框架 (35+ 评估用例)
- **2026-01-08**: 修复后端 API Bug，完善边界测试

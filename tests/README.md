# ChatBot 产品评估框架

## 设计理念

统一所有测试为**评估用例**，在真实后端上运行，使用 LLM-as-Judge 智能评估。

**不使用 Mock 和单元测试**，所有用例都是**真实用户场景**。

## 评估范围

### 通用 ChatBot 能力（任何 ChatBot 都应具备）

| 类别 | 用例数 | 测试内容 |
|-----|-------|---------|
| **basic** | 5 | 问候、知识问答、指令遵循、澄清请求 |
| **context** | 5 | 记忆、指代消解、话题切换、长对话、累积信息 |
| **reasoning** | 6 | 逻辑推理、数学计算、多步骤、常识推理 |
| **code** | 6 | 生成、解释、调试、优化、转换 |
| **language** | 4 | 中英文、翻译、格式化输出 |
| **creative** | 3 | 文案写作、故事创作、头脑风暴 |
| **safety** | 4 | 拒绝有害请求、隐私保护、诚实局限 |
| **robustness** | 5 | 乱码、超长、空输入、模糊指令、错误恢复 |
| **performance** | 2 | 快速响应、复杂任务完成 |

### 本产品独有功能

| 类别 | 用例数 | 测试内容 |
|-----|-------|---------|
| **rag** | 2 | 知识库查询、文档问答 |
| **tools** | 4 | 时间查询、文件操作、Shell 命令、计算 |
| **skills** | 2 | 代码助手、文档助手技能 |
| **intent** | 4 | 查询/操作/分析意图、复合意图 |
| **mcp** | 1 | 外部服务调用 |

**总计：53 个真实场景评估用例**

## 评估维度

| 维度 | 说明 | 权重 |
|-----|------|------|
| accuracy | 准确性 | 20% |
| completeness | 完整性 | 20% |
| relevance | 相关性 | 20% |
| fluency | 流畅性 | 20% |
| helpfulness | 有用性 | 20% |
| context | 上下文保持 | 附加 |
| tool_usage | 工具使用 | 附加 |
| source_citation | 引用来源 | 附加 |

## 运行方式

```bash
# 1. 确保后端运行
cd backend && python run.py &

# 2. 运行完整评估
python tests/evaluation/chatbot_evaluator.py
```

## 评分机制

### 综合得分计算

```
综合得分 = LLM评判(55%) + 维度平均(20%) + 语义匹配(15%) + 工具/延迟(10%) - 安全惩罚
```

### 通过标准

- 综合得分 ≥ 60 分
- 关键用例无错误

## 添加新用例

```python
EvalCase(
    id="unique-id",
    name="用例名称",
    category=EvalCategory.BASIC,  # 或其他类别
    description="测试场景描述",
    
    # 对话流程（真实用户会说的话）
    messages=[
        {"role": "user", "content": "用户第一句话"},
        {"role": "user", "content": "用户第二句话"},
    ],
    
    # 期望（可选）
    expected_answer="期望的关键内容",
    criteria="给 LLM Judge 的评判标准",
    forbidden_content=["禁止出现的内容"],
    
    # 特殊检查（可选）
    should_use_tool="tool_name",
    should_retain_context=True,
    should_cite_source=True,
    max_latency_ms=30000,
    
    # 重要性
    is_critical=True,  # 失败则整体不通过
)
```

## 输出示例

```
📊 ChatBot 产品评估报告
======================================================================

总用例: 53 | 通过: 48 | 通过率: 90.6%
综合得分: 82.5/100 (范围: 45.2 - 98.5)

📈 各类别得分:
  basic: 88.2/100 (5/5 通过)
  context: 85.1/100 (4/5 通过)
  reasoning: 82.3/100 (5/6 通过)
  code: 90.1/100 (6/6 通过)
  ...
  rag: 75.5/100 (1/2 通过)
  tools: 80.2/100 (3/4 通过)
```

# LangChain 1.0 升级日志

> 升级日期: 2025-12-06

## 概述

本次升级将项目从 LangChain v0.x 迁移到 LangChain 1.0，采用全新的 `create_agent` + Middleware 架构。

## 主要变更

### 1. 依赖更新 (`requirements.txt`)

```diff
- langchain>=0.1.0
+ langchain>=1.0.0
+ langchain-core>=0.3.0
+ langgraph>=0.2.0
+ langsmith>=0.1.0
+ langchain-openai>=0.3.0
+ langchain-anthropic>=0.3.0
+ langchain-google-genai>=2.0.0
+ langchain-ollama>=0.3.0
```

### 2. 核心模块重构

#### `langchain_agent.py` - 完全重写
- 使用 `create_agent` 替代手动构建的 Agent 循环
- 实现自定义 `RAGContextMiddleware` 用于上下文注入
- 集成内置 Middleware:
  - `SummarizationMiddleware` - 对话历史压缩
  - `PIIMiddleware` - 敏感信息过滤
  - `HumanInTheLoopMiddleware` - 人工审批
  - `ModelCallLimitMiddleware` - 防止无限循环
  - `ToolRetryMiddleware` - 工具重试
  - `ModelRetryMiddleware` - 模型调用重试
  - `ModelFallbackMiddleware` - 模型故障切换
  - `ToolCallLimitMiddleware` - 工具调用限制
  - `TodoListMiddleware` - 任务列表

#### `agent.py` - 简化为 Wrapper
- 保留 `AgentEngine` 作为主入口
- 委托所有 Agent 逻辑给 `LangChainAgent`
- 专注于上下文加载和 RAG 检索

#### `tools.py` - 新增
- 统一的工具定义模块
- 使用 `@tool` 装饰器
- 内置工具: calculator, get_current_time, get_current_date, word_count 等

#### `llm/client.py` - 更新
- 使用 `init_chat_model` 初始化模型
- 支持模型标识符字符串 (如 `"gpt-4o"`, `"claude-sonnet-4-5"`)
- 自动推断提供商

### 3. 依赖注入更新 (`dependencies.py`)
- 移除废弃的 `get_agent_planner`
- 更新 `get_agent_engine` 支持新的参数
- 添加 LangChain 1.0 特性开关

### 4. API 更新 (`api/chat.py`)
- 移除对废弃组件的引用
- 保持 API 接口兼容性

### 5. 文档更新
- 新增 `docs/LANGCHAIN_1.0_ARCHITECTURE.md`
- 更新 `README.md` 中的代码示例
- 更新 `docs/TARGET.md` 架构图

## 新增功能

### Middleware 支持
| Middleware | 功能 | 默认启用 |
|------------|------|----------|
| RAGContextMiddleware | 注入 RAG 和 @路径上下文 | ✅ |
| SummarizationMiddleware | 对话历史压缩 | ✅ (可选) |
| PIIMiddleware | PII 过滤 | ❌ (可选) |
| HumanInTheLoopMiddleware | 人工审批 | ❌ (可选) |
| ModelFallbackMiddleware | 模型故障切换 | ✅ (可选) |
| TodoListMiddleware | 任务列表 | ❌ (可选) |

### 工具定义
```python
from langchain.tools import tool

@tool
def my_tool(arg: str) -> str:
    """工具描述"""
    return f"Result: {arg}"
```

### 流式输出
```python
async for chunk in agent.chat(message, session_id):
    print(chunk)  # {"type": "text|tool_call|tool_result", "content": ...}
```

## 迁移指南

### 工具迁移
```python
# 旧版
def my_tool(arg):
    return result

# 新版
from langchain.tools import tool

@tool
def my_tool(arg: str) -> str:
    """工具描述"""
    return result
```

### Agent 使用
```python
# 旧版
from langchain.agents import create_react_agent
agent = create_react_agent(llm, tools, prompt)

# 新版
from langchain.agents import create_agent
agent = create_agent(
    model="gpt-4o",
    tools=tools,
    system_prompt="...",
    middleware=[...],
)
```

## 兼容性说明

- API 接口保持向后兼容
- SDK 无需修改
- 配置文件格式不变

## 后续计划

- [ ] 添加单元测试覆盖 Middleware
- [ ] 实现持久化 Checkpointer (PostgreSQL)
- [ ] 添加 LangSmith 集成
- [ ] 优化流式输出性能

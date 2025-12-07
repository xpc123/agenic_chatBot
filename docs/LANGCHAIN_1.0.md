# LangChain 1.0 架构指南

> 本文档详细说明 Agentic ChatBot 如何使用 LangChain 1.0 构建智能代理系统

## 目录

- [概述](#概述)
- [核心组件](#核心组件)
- [create_agent API](#create_agent-api)
- [Middleware 中间件](#middleware-中间件)
- [工具定义](#工具定义)
- [流式输出](#流式输出)
- [持久化](#持久化)
- [最佳实践](#最佳实践)

---

## 概述

LangChain 1.0 是一个简化但功能强大的框架，专注于构建 AI Agent。核心改进包括：

1. **`create_agent`**: 标准化的 Agent 创建 API
2. **Middleware**: 可组合的中间件架构
3. **内置能力**: 持久化、流式输出、人工审批
4. **简化命名空间**: 专注于核心 Agent 构建模块

### 与 v0.x 的区别

| 特性 | LangChain v0.x | LangChain v1.0 |
|------|---------------|----------------|
| Agent 创建 | `create_react_agent` | `create_agent` |
| 上下文工程 | 手动实现 | Middleware |
| 历史管理 | 自定义 | SummarizationMiddleware |
| 工具错误处理 | 手动 | `@wrap_tool_call` |
| 模型切换 | 复杂配置 | `@wrap_model_call` |

---

## 核心组件

### 项目架构

```
backend/app/
├── core/
│   ├── agent.py           # AgentEngine 主入口
│   ├── langchain_agent.py # LangChain 1.0 Agent 实现
│   ├── tools.py           # @tool 工具定义
│   ├── memory.py          # 记忆管理
│   ├── executor.py        # MCP 工具执行器
│   └── context_loader.py  # @路径引用加载
├── llm/
│   └── client.py          # init_chat_model 封装
├── rag/
│   └── retriever.py       # RAG 检索
└── api/
    └── chat.py            # REST/WebSocket API
```

### 数据流

```
用户消息
    ↓
AgentEngine.chat()
    ├── 1. 加载 @路径引用 (ContextLoader)
    ├── 2. RAG 检索 (RAGRetriever)  
    ├── 3. 设置上下文 (RAGContextMiddleware)
    ↓
LangChainAgent.chat()
    ├── create_agent (LangChain 1.0)
    ├── Middleware 链执行
    │   ├── before_model: 注入上下文
    │   ├── model_call: 调用 LLM
    │   ├── tool_call: 执行工具
    │   └── after_model: 后处理
    ↓
流式响应 → 保存记忆 → 返回用户
```

---

## create_agent API

### 基本用法

```python
from langchain.agents import create_agent
from langchain.tools import tool

@tool
def search(query: str) -> str:
    """搜索信息"""
    return f"Results for: {query}"

agent = create_agent(
    model="gpt-4o",                    # 模型标识符
    tools=[search],                     # 工具列表
    system_prompt="你是一个有帮助的助手",  # 系统提示
)

# 调用
result = agent.invoke({
    "messages": [{"role": "user", "content": "搜索天气"}]
})
```

### 完整配置

```python
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import (
    SummarizationMiddleware,
    PIIMiddleware,
    HumanInTheLoopMiddleware,
    ModelCallLimitMiddleware,
)
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model="gpt-4o",
    tools=[tool1, tool2],
    system_prompt="系统提示",
    middleware=[
        ModelCallLimitMiddleware(run_limit=10),
        SummarizationMiddleware(model="gpt-4o-mini", trigger=("tokens", 4000)),
        PIIMiddleware("email", strategy="redact"),
        HumanInTheLoopMiddleware(interrupt_on={"dangerous_tool": True}),
    ],
    checkpointer=InMemorySaver(),      # 持久化
    context_schema=CustomContext,       # 自定义上下文类型
)
```

---

## Middleware 中间件

Middleware 是 LangChain 1.0 的核心创新，提供了在 Agent 执行各阶段插入自定义逻辑的能力。

### 执行流程

```
┌─────────────────────────────────────────────────────────┐
│                    Agent 执行循环                        │
│                                                         │
│  before_agent → [循环开始]                              │
│       ↓                                                 │
│  before_model → wrap_model_call → after_model           │
│       ↓                                                 │
│  [工具调用?]                                             │
│       ↓ Yes                                             │
│  wrap_tool_call                                         │
│       ↓                                                 │
│  [继续循环或结束]                                        │
│       ↓                                                 │
│  after_agent                                            │
└─────────────────────────────────────────────────────────┘
```

### 内置 Middleware

| Middleware | 功能 | 使用场景 |
|------------|------|----------|
| `SummarizationMiddleware` | 自动压缩对话历史 | 长对话 |
| `PIIMiddleware` | 敏感信息过滤 | 隐私保护 |
| `HumanInTheLoopMiddleware` | 人工审批 | 高风险操作 |
| `ModelCallLimitMiddleware` | 限制模型调用次数 | 防止无限循环 |
| `ToolCallLimitMiddleware` | 限制工具调用次数 | 成本控制 |
| `ModelFallbackMiddleware` | 模型故障切换 | 高可用 |
| `ToolRetryMiddleware` | 工具自动重试 | 容错 |
| `ModelRetryMiddleware` | 模型调用重试 | 容错 |
| `TodoListMiddleware` | 任务列表管理 | 复杂任务 |
| `LLMToolSelectorMiddleware` | 智能工具选择 | 多工具场景 |

### 自定义 Middleware

#### 方式一：装饰器

```python
from langchain.agents.middleware import before_model, after_model, wrap_tool_call

@before_model
def inject_context(request):
    """在模型调用前注入上下文"""
    messages = list(request.state.get("messages", []))
    messages.insert(0, SystemMessage(content="额外上下文..."))
    return {"messages": messages}

@wrap_tool_call
def log_tool_calls(request, handler):
    """记录所有工具调用"""
    print(f"Calling tool: {request.tool_call['name']}")
    return handler(request)
```

#### 方式二：类

```python
from langchain.agents.middleware import AgentMiddleware

class CustomMiddleware(AgentMiddleware):
    def before_model(self, state, runtime):
        """模型调用前"""
        return None  # 返回 None 表示不修改
    
    def after_model(self, state, response, runtime):
        """模型调用后"""
        pass
    
    def wrap_model_call(self, request, handler):
        """包装模型调用"""
        return handler(request)
    
    def wrap_tool_call(self, request, handler):
        """包装工具调用"""
        return handler(request)
```

---

## 工具定义

### 基本工具

```python
from langchain.tools import tool

@tool
def calculator(expression: str) -> str:
    """计算数学表达式"""
    return str(eval(expression))
```

### 异步工具

```python
@tool
async def fetch_data(url: str) -> str:
    """获取远程数据"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()
```

### 使用运行时上下文

```python
from langchain.tools import tool, ToolRuntime
from dataclasses import dataclass

@dataclass
class UserContext:
    user_id: str
    permissions: list

@tool
def get_user_data(runtime: ToolRuntime[UserContext]) -> str:
    """获取当前用户数据"""
    user_id = runtime.context.user_id
    return f"User: {user_id}"
```

---

## 流式输出

### 基本流式

```python
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "问题"}]},
    stream_mode="values"
):
    messages = chunk.get("messages", [])
    if messages:
        print(messages[-1].content)
```

### 异步流式

```python
async for chunk in agent.astream(
    {"messages": [{"role": "user", "content": "问题"}]},
    stream_mode="values"
):
    # 处理 chunk
    pass
```

### 流式模式

- `"values"`: 每次返回完整状态
- `"updates"`: 只返回变更部分
- `"messages"`: 只返回消息

---

## 持久化

### 内存持久化

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()

agent = create_agent(
    model="gpt-4o",
    tools=[...],
    checkpointer=checkpointer,
)

# 使用 thread_id 区分会话
config = {"configurable": {"thread_id": "session-123"}}
agent.invoke({"messages": [...]}, config)
```

### 数据库持久化

```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string("postgresql://...")

agent = create_agent(
    model="gpt-4o",
    tools=[...],
    checkpointer=checkpointer,
)
```

---

## 最佳实践

### 1. 工具设计

- ✅ 提供清晰的文档字符串
- ✅ 使用类型注解
- ✅ 返回格式化的结果
- ❌ 避免在工具中抛出未捕获的异常

### 2. Middleware 顺序

```python
middleware = [
    # 1. 限制类（最先）
    ModelCallLimitMiddleware(...),
    ToolCallLimitMiddleware(...),
    
    # 2. 重试类
    ModelRetryMiddleware(...),
    ToolRetryMiddleware(...),
    
    # 3. 上下文类
    SummarizationMiddleware(...),
    CustomContextMiddleware(),
    
    # 4. 安全类
    PIIMiddleware(...),
    
    # 5. 审批类（最后）
    HumanInTheLoopMiddleware(...),
]
```

### 3. 错误处理

```python
@wrap_tool_call
def handle_errors(request, handler):
    try:
        return handler(request)
    except Exception as e:
        return ToolMessage(
            content=f"Error: {e}",
            tool_call_id=request.tool_call["id"]
        )
```

### 4. 性能优化

- 使用 `gpt-4o-mini` 作为 SummarizationMiddleware 的模型
- 设置合理的 `trigger` 阈值
- 使用 `LLMToolSelectorMiddleware` 减少工具数量
- 启用 `ModelFallbackMiddleware` 提高可用性

---

## 参考资源

- [LangChain 1.0 官方文档](https://docs.langchain.com/oss/python/langchain/overview)
- [Middleware 指南](https://docs.langchain.com/oss/python/langchain/middleware)
- [create_agent 参考](https://reference.langchain.com/python/langchain/agents)
- [迁移指南](https://docs.langchain.com/oss/python/migrate/langchain-v1)

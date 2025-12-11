# Context 快速集成指南

> **核心理念**: 上下文即能力 - 你给 AI 什么上下文，它就有什么能力

## 🎯 为什么 Context 是集成关键？

传统 AI 集成需要你理解：
- ❌ LLM 模型原理
- ❌ RAG 检索技术  
- ❌ Agent 规划算法
- ❌ Prompt Engineering

**使用 Agentic ChatBot，你只需要**：
- ✅ **提供上下文** - 你的产品有什么数据？
- ✅ **设置优先级** - 什么最重要？
- ✅ **获得能力** - AI 自动处理其余一切

---

## ⚡ 5 分钟快速开始

### 1. 创建 ContextManager

```python
from app.core.context_manager import ContextManager, ContextPriority

# 创建上下文管理器
ctx = ContextManager(max_tokens=8000)
```

### 2. 添加你的产品上下文

```python
# 链式调用（推荐）
ctx = (ContextManager(max_tokens=8000)
       .add_custom("current_state", your_app_state, priority=ContextPriority.HIGH)
       .add_custom("user_data", user_info, priority=ContextPriority.MEDIUM)
       .add_rag_results(knowledge_base))

# 构建统一上下文
unified_context = ctx.build()
```

### 3. 传递给 Agent

```python
from app.core import AgentEngine

agent = AgentEngine()
async for chunk in agent.chat(
    message="用户问题",
    session_id="session_123",
    context=unified_context
):
    print(chunk)
```

---

## 📦 预设模板 - 开箱即用

### IDE / 代码编辑器

```python
from app.core.context_manager import ContextManager

# 一行代码配置 IDE 上下文
ctx = ContextManager.for_ide(
    workspace_path="/path/to/project",
    current_file="src/main.py",
    diagnostics=[
        {"line": 10, "message": "undefined variable 'x'"},
        {"line": 25, "message": "unused import"}
    ],
    git_info={
        "branch": "feature/new-ui",
        "modified_files": ["src/main.py", "src/utils.py"]
    }
)

# 就这样！AI 现在理解你的代码上下文
```

**AI 自动获得的能力**：
- ✅ 理解当前工作空间结构
- ✅ 知道正在编辑哪个文件
- ✅ 看到代码诊断错误
- ✅ 了解 Git 状态

### 数据分析工具

```python
# Pandas / Jupyter Notebook 集成
ctx = ContextManager.for_data_analysis(
    dataframe_info={
        "shape": (1000, 10),
        "columns": ["id", "name", "age", "city", "salary"],
        "dtypes": {"id": "int64", "name": "object", "age": "int64"},
        "sample": df.head(3).to_dict()
    },
    query_history=[
        "SELECT * FROM users WHERE age > 30",
        "df.groupby('city').mean()"
    ],
    visualization_context="当前图表：年龄分布直方图"
)
```

**AI 自动获得的能力**：
- ✅ 理解数据结构和类型
- ✅ 基于历史查询给出建议
- ✅ 根据当前可视化提供分析

### 客服系统

```python
# 客服机器人集成
ctx = ContextManager.for_customer_service(
    user_profile={
        "id": "U12345",
        "name": "张三",
        "vip_level": "gold",
        "register_date": "2023-01-15"
    },
    order_history=[
        {"id": "O001", "product": "iPhone", "status": "shipped"},
        {"id": "O002", "product": "AirPods", "status": "delivered"}
    ],
    knowledge_base=[
        {"content": "退货政策：7天无理由退货", "score": 0.95},
        {"content": "会员权益：积分翻倍", "score": 0.88}
    ]
)
```

**AI 自动获得的能力**：
- ✅ 识别用户身份和会员等级
- ✅ 查看订单历史
- ✅ 基于知识库回答问题

### 文档编辑器

```python
# Word / Notion 类产品集成
ctx = ContextManager.for_document_editor(
    document_metadata={
        "title": "2025 产品规划",
        "author": "产品团队",
        "tags": ["规划", "2025", "roadmap"],
        "word_count": 2500
    },
    current_selection="这段文字需要润色和改进",
    writing_style="正式、专业、面向高管"
)
```

**AI 自动获得的能力**：
- ✅ 理解文档主题和目标读者
- ✅ 根据选中内容提供精准建议
- ✅ 遵循写作风格偏好

---

## 🎨 自定义上下文

### 添加自定义上下文

```python
ctx = ContextManager()

# 高优先级 - 重要信息（用户显式指定）
ctx.add_custom(
    name="current_page",
    content="用户正在查看产品列表页面",
    priority=ContextPriority.HIGH
)

# 中优先级 - 一般信息（系统状态）
ctx.add_custom(
    name="app_state",
    content=f"当前过滤条件: {filters}",
    priority=ContextPriority.MEDIUM
)

# 低优先级 - 辅助信息（历史记录）
ctx.add_custom(
    name="recent_actions",
    content="最近操作: 添加到购物车 -> 查看详情",
    priority=ContextPriority.LOW
)
```

### 优先级说明

| 优先级 | 使用场景 | 示例 |
|--------|----------|------|
| **CRITICAL** | 系统指令、安全规则 | "不要泄露用户密码" |
| **HIGH** | 用户显式指定的内容 | @文件引用、当前选中文本 |
| **MEDIUM** | 系统状态、工具信息 | 可用工具、数据结构 |
| **LOW** | 历史记录、偏好设置 | 操作历史、用户偏好 |

---

## 🔧 高级用法

### 1. Token 预算控制

```python
# 自动控制 token 使用
ctx = ContextManager(
    max_tokens=8000,        # 最大 8000 tokens
    reserve_tokens=2000     # 预留 2000 tokens 给响应
)

# ContextManager 自动:
# - 按优先级保留重要信息
# - 截断低优先级信息
# - 确保不超过 token 限制
```

### 2. 动态上下文

```python
def get_context_for_user_action(action: str):
    ctx = ContextManager()
    
    if action == "code_review":
        ctx.add_custom("task", "代码审查", ContextPriority.HIGH)
        ctx.add_custom("checklist", code_review_checklist, ContextPriority.MEDIUM)
    
    elif action == "bug_fix":
        ctx.add_custom("task", "修复 Bug", ContextPriority.HIGH)
        ctx.add_custom("error_logs", recent_errors, ContextPriority.HIGH)
    
    return ctx
```

### 3. 上下文组合

```python
# 组合多种上下文来源
ctx = (ContextManager()
       # 产品特定上下文
       .add_custom("workspace", workspace_info, ContextPriority.HIGH)
       # RAG 知识库
       .add_rag_results(knowledge_base_results)
       # MCP 工具
       .add_mcp_tools(available_tools)
       # 用户偏好
       .add_user_preferences(user_settings))

unified_context = ctx.build()
```

### 4. 调试和监控

```python
# 获取统计信息
stats = ctx.get_stats()
print(f"""
上下文统计:
- 总项数: {stats['total_items']}
- Token 使用: {stats['used_tokens']}/{stats['max_tokens']}
- 路径引用: {stats['path_references_count']} 个
- RAG 结果: {stats['rag_results_count']} 个
- 自定义上下文: {stats['custom_contexts_count']} 个
""")

# 查看已添加的上下文来源
sources = ctx.get_context_sources()
print(f"已添加的上下文: {', '.join(sources)}")
```

---

## 💡 最佳实践

### 1. 分清优先级

```python
# ✅ 好的做法
ctx.add_custom("user_question", user_input, ContextPriority.HIGH)       # 用户问题最重要
ctx.add_custom("app_state", current_state, ContextPriority.MEDIUM)      # 应用状态次要
ctx.add_custom("history", action_log, ContextPriority.LOW)              # 历史记录最低

# ❌ 不好的做法
ctx.add_custom("everything", all_data, ContextPriority.HIGH)  # 不要全部标记为高优先级
```

### 2. 提供结构化信息

```python
# ✅ 好的做法 - 结构化
dataframe_info = {
    "shape": (1000, 5),
    "columns": ["id", "name", "age"],
    "dtypes": {"id": "int", "name": "str"}
}
ctx.add_custom("dataframe", json.dumps(dataframe_info, indent=2))

# ❌ 不好的做法 - 纯文本
ctx.add_custom("dataframe", "有一个表格，很多数据")
```

### 3. 避免重复信息

```python
# ✅ 好的做法
ctx.add_custom("project_structure", tree, ContextPriority.MEDIUM)

# ❌ 不好的做法 - 重复信息
ctx.add_custom("project_structure", tree, ContextPriority.MEDIUM)
ctx.add_custom("file_list", file_list, ContextPriority.MEDIUM)  # 重复
ctx.add_custom("directory_tree", tree, ContextPriority.MEDIUM)   # 重复
```

### 4. 动态调整 Token 预算

```python
# 根据任务复杂度调整
def get_context_manager(task_complexity: str):
    if task_complexity == "simple":
        return ContextManager(max_tokens=4000, reserve_tokens=1000)
    elif task_complexity == "complex":
        return ContextManager(max_tokens=12000, reserve_tokens=3000)
    else:
        return ContextManager(max_tokens=8000, reserve_tokens=2000)
```

---

## 🚀 完整集成示例

### Jupyter Notebook 插件

```python
# 1. 在 Jupyter 单元格执行时捕获上下文
def capture_notebook_context(ipython):
    ctx = ContextManager.for_data_analysis(
        dataframe_info={
            "shape": df.shape,
            "columns": list(df.columns),
            "dtypes": df.dtypes.to_dict(),
            "sample": df.head(3).to_dict()
        },
        query_history=ipython.history_manager.get_tail(5)
    )
    return ctx

# 2. 在魔法命令中使用
@register_line_magic
def ai(line):
    ctx = capture_notebook_context(get_ipython())
    agent = AgentEngine()
    
    response = ""
    async for chunk in agent.chat(line, context=ctx.build()):
        if chunk["type"] == "text":
            response += chunk["content"]
    
    return response

# 3. 用户使用
# %ai 如何分析年龄和薪资的关系？
```

### VS Code 插件

```python
# extension.py
import vscode
from chatbot_sdk import ChatBot, ContextManager, ContextPriority

def activate(context):
    # 注册命令
    def chat_command():
        # 1. 收集 IDE 上下文
        editor = vscode.window.active_text_editor
        workspace = vscode.workspace.workspace_folders[0]
        diagnostics = vscode.languages.get_diagnostics(editor.document.uri)
        
        # 2. 构建上下文
        ctx = ContextManager.for_ide(
            workspace_path=workspace.uri.fs_path,
            current_file=editor.document.file_name,
            diagnostics=[
                {"line": d.range.start.line, "message": d.message}
                for d in diagnostics
            ]
        )
        
        # 3. 调用 AI
        bot = ChatBot(base_url="http://localhost:8000")
        response = bot.chat_with_context(
            message=vscode.window.show_input_box("问 AI"),
            context=ctx
        )
        
        # 4. 显示结果
        vscode.window.show_information_message(response)
    
    context.subscriptions.append(
        vscode.commands.register_command('extension.aiChat', chat_command)
    )
```

---

## 📊 Context 能力对照表

| 产品类型 | 提供的上下文 | AI 获得的能力 |
|----------|-------------|--------------|
| **IDE** | 代码文件、诊断、Git 状态 | 代码理解、错误修复、重构建议 |
| **数据分析** | DataFrame 结构、查询历史 | SQL 生成、数据分析、可视化建议 |
| **客服** | 用户资料、订单、知识库 | 个性化回答、订单查询、问题解决 |
| **文档编辑** | 文档元数据、选中文本 | 内容润色、写作建议、格式优化 |
| **项目管理** | 任务列表、进度、成员 | 任务分配、进度跟踪、风险提醒 |

---

## 🎓 常见问题

### Q1: 我需要理解 LLM 原理吗？
**A**: 不需要！只需要知道：**给什么上下文 = 得到什么能力**

### Q2: Token 限制怎么办？
**A**: ContextManager 自动处理！按优先级保留重要信息，自动截断低优先级内容。

### Q3: 如何知道添加了哪些上下文？
**A**: 使用 `ctx.get_stats()` 和 `ctx.get_context_sources()` 查看详细信息。

### Q4: 可以动态调整上下文吗？
**A**: 可以！根据用户操作动态添加或清除上下文。

### Q5: 预设模板不满足需求怎么办？
**A**: 使用 `add_custom()` 添加自定义上下文，完全灵活！

---

## 🔗 相关文档

- [快速开始](./QUICKSTART.md) - 5 分钟完整集成流程
- [架构说明](./ARCHITECTURE.md) - 理解系统设计
- [API 文档](./API.md) - 完整 API 参考

---

**记住核心理念**: 你不需要成为 AI 专家，只需要了解你的产品有什么数据！

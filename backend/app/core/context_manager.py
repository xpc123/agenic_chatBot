# -*- coding: utf-8 -*-
"""
上下文管理器 - Context Engineering

统一管理所有上下文来源:
1. MCP Server 工具信息
2. 路径引用 (@path)
3. RAG 检索结果
4. Skills 技能描述
5. 对话历史
6. 用户偏好
7. 系统指令
"""
from typing import Dict, List, Any, Optional
from loguru import logger
from enum import Enum


class ContextPriority(Enum):
    """上下文优先级"""
    CRITICAL = 1    # 系统指令、安全规则
    HIGH = 2        # @路径引用、用户显式指定
    MEDIUM = 3      # MCP工具、Skills、RAG结果
    LOW = 4         # 对话历史、用户偏好
    

class ContextSource:
    """上下文来源"""
    SYSTEM = "system"           # 系统指令
    PATH_REFERENCE = "path"     # @路径引用
    MCP_SERVER = "mcp"          # MCP Server 工具
    RAG = "rag"                 # RAG 检索结果
    SKILLS = "skills"           # Skills 技能
    HISTORY = "history"         # 对话历史
    PREFERENCES = "preferences" # 用户偏好
    CUSTOM = "custom"           # 自定义上下文


class ContextManager:
    """
    统一上下文管理器 - 快速集成的核心
    
    负责:
    1. 收集各种上下文来源（MCP、@引用、RAG、Skills等）
    2. 按优先级自动排序
    3. Token 预算自动控制
    4. 构建最终上下文
    
    核心理念: **上下文即能力** - 产品方只需关注提供什么上下文，就能获得相应的 AI 能力
    
    使用示例:
    ```python
    # 基础用法
    ctx = ContextManager(max_tokens=8000)
    ctx.add_mcp_tools(tools)
    ctx.add_path_references(references)
    ctx.add_rag_results(results)
    unified_context = ctx.build()
    
    # 链式调用（推荐）
    ctx = (ContextManager(max_tokens=8000)
           .add_custom("current_file", file_content, priority=ContextPriority.HIGH)
           .add_custom("project_structure", tree, priority=ContextPriority.MEDIUM)
           .add_rag_results(knowledge_base))
    unified_context = ctx.build()
    
    # 快速集成 - IDE 产品示例
    ctx = ContextManager.for_ide(
        workspace_path="/path/to/project",
        current_file="src/main.py",
        diagnostics=lsp_errors
    )
    ```
    """
    
    def __init__(
        self,
        max_tokens: int = 8000,
        reserve_tokens: int = 2000,
    ):
        """
        初始化上下文管理器
        
        Args:
            max_tokens: 最大 Token 数
            reserve_tokens: 预留 Token 数（用于响应）
        """
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens
        self.available_tokens = max_tokens - reserve_tokens
        
        # 上下文存储（按来源分类）
        self.contexts: Dict[str, Dict[str, Any]] = {
            ContextSource.SYSTEM: {"data": None, "priority": ContextPriority.CRITICAL},
            ContextSource.PATH_REFERENCE: {"data": None, "priority": ContextPriority.HIGH},
            ContextSource.MCP_SERVER: {"data": None, "priority": ContextPriority.MEDIUM},
            ContextSource.RAG: {"data": None, "priority": ContextPriority.MEDIUM},
            ContextSource.SKILLS: {"data": None, "priority": ContextPriority.MEDIUM},
            ContextSource.HISTORY: {"data": None, "priority": ContextPriority.LOW},
            ContextSource.PREFERENCES: {"data": None, "priority": ContextPriority.LOW},
            ContextSource.CUSTOM: {"data": None, "priority": ContextPriority.LOW},
        }
        
        # 统计信息
        self.stats = {
            "system_instructions": False,
            "path_references_count": 0,
            "mcp_tools_count": 0,
            "mcp_servers_count": 0,
            "rag_results_count": 0,
            "skills_count": 0,
            "history_messages_count": 0,
            "has_preferences": False,
            "custom_contexts_count": 0,
        }
        
        logger.debug(f"ContextManager initialized: max_tokens={max_tokens}, reserve={reserve_tokens}")
    
    # ==================== 添加上下文方法 ====================
    
    def add_system_instructions(self, instructions: str) -> "ContextManager":
        """
        添加系统指令（最高优先级）
        
        Args:
            instructions: 系统指令文本
        
        Returns:
            self (支持链式调用)
        """
        self.contexts[ContextSource.SYSTEM]["data"] = instructions
        self.stats["system_instructions"] = True
        logger.debug("System instructions added")
        return self
    
    def add_path_references(self, references: Dict[str, Any]) -> "ContextManager":
        """
        添加 @路径引用上下文
        
        Args:
            references: 路径引用数据，包含 contexts, formatted 等
        
        Returns:
            self (支持链式调用)
        """
        self.contexts[ContextSource.PATH_REFERENCE]["data"] = references
        self.stats["path_references_count"] = references.get("references_count", 0)
        logger.debug(f"Path references added: {self.stats['path_references_count']} refs")
        return self
    
    def add_mcp_tools(
        self, 
        tools: List[Any], 
        servers: Optional[List[Any]] = None
    ) -> "ContextManager":
        """
        添加 MCP Server 工具信息
        
        Args:
            tools: MCP 工具列表
            servers: MCP 服务器列表（可选）
        
        Returns:
            self (支持链式调用)
        """
        self.contexts[ContextSource.MCP_SERVER]["data"] = {
            "tools": tools,
            "servers": servers or [],
        }
        self.stats["mcp_tools_count"] = len(tools)
        self.stats["mcp_servers_count"] = len(servers) if servers else 0
        logger.debug(f"MCP tools added: {len(tools)} tools from {self.stats['mcp_servers_count']} servers")
        return self
    
    def add_rag_results(self, results: List[Dict[str, Any]]) -> "ContextManager":
        """
        添加 RAG 检索结果
        
        Args:
            results: RAG 检索结果列表
        
        Returns:
            self (支持链式调用)
        """
        self.contexts[ContextSource.RAG]["data"] = results
        self.stats["rag_results_count"] = len(results)
        logger.debug(f"RAG results added: {len(results)} documents")
        return self
    
    def add_skills(self, skills: List[Dict[str, Any]]) -> "ContextManager":
        """
        添加 Skills 技能描述
        
        Args:
            skills: 技能列表，每个技能包含 name, description, examples 等
        
        Returns:
            self (支持链式调用)
        """
        self.contexts[ContextSource.SKILLS]["data"] = skills
        self.stats["skills_count"] = len(skills)
        logger.debug(f"Skills added: {len(skills)} skills")
        return self
    
    def add_conversation_history(self, history: List[Dict[str, str]]) -> "ContextManager":
        """
        添加对话历史
        
        Args:
            history: 对话历史列表
        
        Returns:
            self (支持链式调用)
        """
        self.contexts[ContextSource.HISTORY]["data"] = history
        self.stats["history_messages_count"] = len(history)
        logger.debug(f"Conversation history added: {len(history)} messages")
        return self
    
    def add_user_preferences(self, preferences: Dict[str, Any]) -> "ContextManager":
        """
        添加用户偏好
        
        Args:
            preferences: 用户偏好字典
        
        Returns:
            self (支持链式调用)
        """
        self.contexts[ContextSource.PREFERENCES]["data"] = preferences
        self.stats["has_preferences"] = True
        logger.debug("User preferences added")
        return self
    
    def add_custom_context(
        self, 
        name: str, 
        content: str, 
        priority: ContextPriority = ContextPriority.MEDIUM
    ) -> "ContextManager":
        """
        添加自定义上下文
        
        Args:
            name: 上下文名称
            content: 上下文内容
            priority: 优先级
        
        Returns:
            self (支持链式调用)
        """
        if self.contexts[ContextSource.CUSTOM]["data"] is None:
            self.contexts[ContextSource.CUSTOM]["data"] = []
        
        self.contexts[ContextSource.CUSTOM]["data"].append({
            "name": name,
            "content": content,
            "priority": priority,
        })
        self.stats["custom_contexts_count"] += 1
        logger.debug(f"Custom context added: {name}")
        return self
    
    # ==================== 构建上下文 ====================
    
    def build(self) -> str:
        """
        构建统一上下文
        
        按优先级组装:
        1. 系统指令 (CRITICAL)
        2. @路径引用 (HIGH)
        3. MCP 工具 (MEDIUM)
        4. Skills (MEDIUM)
        5. RAG 结果 (MEDIUM)
        6. 用户偏好 (LOW)
        7. 自定义上下文 (按各自优先级)
        
        注意：对话历史通常由 Agent 的 memory 管理，不在这里添加
        
        Returns:
            格式化的上下文字符串
        """
        parts = []
        current_tokens = 0
        
        # 1. 系统指令 (CRITICAL)
        system_data = self.contexts[ContextSource.SYSTEM]["data"]
        if system_data:
            parts.append(f"## 系统指令\n{system_data}")
            current_tokens += self.estimate_tokens(system_data)
        
        # 2. @路径引用 (HIGH) - 用户显式指定，高优先级
        path_data = self.contexts[ContextSource.PATH_REFERENCE]["data"]
        if path_data:
            formatted = path_data.get("formatted", "")
            if formatted:
                parts.append(f"## 引用的文件内容\n{formatted}")
                current_tokens += self.estimate_tokens(formatted)
        
        # 3. MCP 工具 (MEDIUM)
        mcp_data = self.contexts[ContextSource.MCP_SERVER]["data"]
        if mcp_data:
            mcp_text = self._format_mcp_tools(mcp_data)
            if mcp_text and current_tokens + self.estimate_tokens(mcp_text) <= self.available_tokens:
                parts.append(f"## 可用工具 (MCP)\n{mcp_text}")
                current_tokens += self.estimate_tokens(mcp_text)
        
        # 4. Skills (MEDIUM)
        skills_data = self.contexts[ContextSource.SKILLS]["data"]
        if skills_data:
            skills_text = self._format_skills(skills_data)
            if skills_text and current_tokens + self.estimate_tokens(skills_text) <= self.available_tokens:
                parts.append(f"## 可用技能\n{skills_text}")
                current_tokens += self.estimate_tokens(skills_text)
        
        # 5. RAG 结果 (MEDIUM)
        rag_data = self.contexts[ContextSource.RAG]["data"]
        if rag_data:
            rag_text = self._format_rag_results(rag_data)
            if rag_text and current_tokens + self.estimate_tokens(rag_text) <= self.available_tokens:
                parts.append(f"## 相关知识\n{rag_text}")
                current_tokens += self.estimate_tokens(rag_text)
        
        # 6. 用户偏好 (LOW)
        pref_data = self.contexts[ContextSource.PREFERENCES]["data"]
        if pref_data:
            pref_text = self._format_preferences(pref_data)
            if pref_text and current_tokens + self.estimate_tokens(pref_text) <= self.available_tokens:
                parts.append(f"## 用户偏好\n{pref_text}")
                current_tokens += self.estimate_tokens(pref_text)
        
        # 7. 自定义上下文
        custom_data = self.contexts[ContextSource.CUSTOM]["data"]
        if custom_data:
            for ctx in sorted(custom_data, key=lambda x: x["priority"].value):
                ctx_text = f"### {ctx['name']}\n{ctx['content']}"
                if current_tokens + self.estimate_tokens(ctx_text) <= self.available_tokens:
                    parts.append(ctx_text)
                    current_tokens += self.estimate_tokens(ctx_text)
        
        if not parts:
            return ""
        
        result = "\n\n".join(parts)
        logger.info(f"Context built: {current_tokens} tokens, {len(parts)} sections")
        return result
    
    # ==================== 格式化方法 ====================
    
    def _format_mcp_tools(self, mcp_data: Dict[str, Any]) -> str:
        """格式化 MCP 工具信息"""
        tools = mcp_data.get("tools", [])
        servers = mcp_data.get("servers", [])
        
        if not tools:
            return ""
        
        lines = []
        
        # 服务器信息
        if servers:
            server_names = [s.name if hasattr(s, 'name') else str(s) for s in servers]
            lines.append(f"已连接服务器: {', '.join(server_names)}")
            lines.append("")
        
        # 工具列表
        lines.append("可用工具:")
        for tool in tools:
            name = tool.name if hasattr(tool, 'name') else tool.get('name', 'unknown')
            desc = tool.description if hasattr(tool, 'description') else tool.get('description', '')
            server = tool.server_name if hasattr(tool, 'server_name') else tool.get('server_name', '')
            
            if server:
                lines.append(f"- **{name}** ({server}): {desc}")
            else:
                lines.append(f"- **{name}**: {desc}")
        
        return "\n".join(lines)
    
    def _format_skills(self, skills: List[Dict[str, Any]]) -> str:
        """格式化 Skills 技能描述"""
        if not skills:
            return ""
        
        lines = []
        for skill in skills:
            name = skill.get("name", "unknown")
            desc = skill.get("description", "")
            examples = skill.get("examples", [])
            
            lines.append(f"### {name}")
            if desc:
                lines.append(desc)
            if examples:
                lines.append("示例:")
                for ex in examples[:3]:  # 最多3个示例
                    lines.append(f"  - {ex}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_rag_results(self, results: List[Dict[str, Any]]) -> str:
        """格式化 RAG 结果"""
        if not results:
            return ""
        
        parts = []
        for i, result in enumerate(results, 1):
            content = result.get("content", "")
            source = result.get("source", "unknown")
            score = result.get("score", 0)
            
            if isinstance(score, (int, float)):
                parts.append(f"### 来源 {i}: {source} (相关度: {score:.2f})\n{content}")
            else:
                parts.append(f"### 来源 {i}: {source}\n{content}")
        
        return "\n\n".join(parts)
    
    def _format_preferences(self, preferences: Dict[str, Any]) -> str:
        """格式化用户偏好"""
        if not preferences:
            return ""
        
        lines = []
        for key, value in preferences.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)
    
    # ==================== 工具方法 ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计字典
        """
        total_items = (
            (1 if self.stats["system_instructions"] else 0) +
            self.stats["path_references_count"] +
            self.stats["mcp_tools_count"] +
            self.stats["rag_results_count"] +
            self.stats["skills_count"] +
            self.stats["history_messages_count"] +
            (1 if self.stats["has_preferences"] else 0) +
            self.stats["custom_contexts_count"]
        )
        
        return {
            **self.stats,
            "total_items": total_items,
            "max_tokens": self.max_tokens,
            "available_tokens": self.available_tokens,
            "utilization_percent": f"{(total_items / max(1, self.max_tokens)) * 100:.1f}%",
        }
    
    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的 Token 数
        
        简单估算：中文约 2 字符/token，英文约 4 字符/token
        混合内容取平均值约 3 字符/token
        """
        if not text:
            return 0
        return len(text) // 3
    
    def clear(self) -> None:
        """清空所有上下文"""
        for source in self.contexts:
            self.contexts[source]["data"] = None
        
        self.stats = {
            "system_instructions": False,
            "path_references_count": 0,
            "mcp_tools_count": 0,
            "mcp_servers_count": 0,
            "rag_results_count": 0,
            "skills_count": 0,
            "history_messages_count": 0,
            "has_preferences": False,
            "custom_contexts_count": 0,
        }
        logger.debug("ContextManager cleared")
    
    def get_context_sources(self) -> List[str]:
        """
        获取当前已添加的上下文来源列表
        
        Returns:
            来源名称列表
        """
        sources = []
        for source, ctx in self.contexts.items():
            if ctx["data"] is not None:
                sources.append(source)
        return sources
    
    # ==================== 便捷工厂方法 ====================
    
    @classmethod
    def for_ide(
        cls,
        workspace_path: Optional[str] = None,
        current_file: Optional[str] = None,
        diagnostics: Optional[List[Dict]] = None,
        git_info: Optional[Dict] = None,
        max_tokens: int = 8000,
    ) -> "ContextManager":
        """
        IDE/代码编辑器产品的快速集成模板
        
        Args:
            workspace_path: 工作空间路径
            current_file: 当前打开的文件路径
            diagnostics: LSP 诊断信息（错误、警告等）
            git_info: Git 状态信息
            max_tokens: Token 限制
        
        Returns:
            配置好的 ContextManager 实例
        
        示例:
            ```python
            ctx = ContextManager.for_ide(
                workspace_path="/project",
                current_file="src/main.py",
                diagnostics=[{"line": 10, "message": "undefined variable"}]
            )
            ```
        """
        ctx = cls(max_tokens=max_tokens)
        
        if workspace_path:
            ctx.add_custom(
                "workspace_info",
                f"工作空间路径: {workspace_path}",
                priority=ContextPriority.MEDIUM
            )
        
        if current_file:
            ctx.add_custom(
                "current_file",
                f"当前文件: {current_file}",
                priority=ContextPriority.HIGH
            )
        
        if diagnostics:
            diagnostics_text = "\n".join([
                f"- 行 {d.get('line', '?')}: {d.get('message', '')}"
                for d in diagnostics
            ])
            ctx.add_custom(
                "diagnostics",
                f"代码诊断信息:\n{diagnostics_text}",
                priority=ContextPriority.HIGH
            )
        
        if git_info:
            git_text = f"Git 分支: {git_info.get('branch', 'unknown')}"
            if git_info.get('modified_files'):
                git_text += f"\n修改的文件: {', '.join(git_info['modified_files'])}"
            ctx.add_custom(
                "git_status",
                git_text,
                priority=ContextPriority.LOW
            )
        
        return ctx
    
    @classmethod
    def for_data_analysis(
        cls,
        dataframe_info: Optional[Dict] = None,
        query_history: Optional[List[str]] = None,
        visualization_context: Optional[str] = None,
        max_tokens: int = 8000,
    ) -> "ContextManager":
        """
        数据分析工具的快速集成模板
        
        Args:
            dataframe_info: DataFrame 元信息（schema, shape 等）
            query_history: 查询历史
            visualization_context: 当前可视化上下文
            max_tokens: Token 限制
        
        Returns:
            配置好的 ContextManager 实例
        
        示例:
            ```python
            ctx = ContextManager.for_data_analysis(
                dataframe_info={
                    "shape": (1000, 10),
                    "columns": ["id", "name", "age"],
                    "dtypes": {"id": "int", "name": "str"}
                },
                query_history=["SELECT * FROM users", "..."]
            )
            ```
        """
        ctx = cls(max_tokens=max_tokens)
        
        if dataframe_info:
            info_text = []
            if dataframe_info.get('shape'):
                info_text.append(f"数据形状: {dataframe_info['shape']}")
            if dataframe_info.get('columns'):
                info_text.append(f"列名: {', '.join(dataframe_info['columns'])}")
            if dataframe_info.get('dtypes'):
                dtype_text = ', '.join([f"{k}: {v}" for k, v in dataframe_info['dtypes'].items()])
                info_text.append(f"数据类型: {dtype_text}")
            
            ctx.add_custom(
                "dataframe_info",
                "\n".join(info_text),
                priority=ContextPriority.HIGH
            )
        
        if query_history:
            history_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(query_history[-5:])])
            ctx.add_custom(
                "query_history",
                f"最近的查询:\n{history_text}",
                priority=ContextPriority.LOW
            )
        
        if visualization_context:
            ctx.add_custom(
                "visualization",
                visualization_context,
                priority=ContextPriority.MEDIUM
            )
        
        return ctx
    
    @classmethod
    def for_customer_service(
        cls,
        user_profile: Optional[Dict] = None,
        order_history: Optional[List[Dict]] = None,
        knowledge_base: Optional[List[Dict]] = None,
        max_tokens: int = 8000,
    ) -> "ContextManager":
        """
        客服系统的快速集成模板
        
        Args:
            user_profile: 用户资料
            order_history: 订单历史
            knowledge_base: 知识库内容
            max_tokens: Token 限制
        
        Returns:
            配置好的 ContextManager 实例
        
        示例:
            ```python
            ctx = ContextManager.for_customer_service(
                user_profile={"id": "123", "vip_level": "gold"},
                order_history=[{"id": "O001", "status": "shipped"}]
            )
            ```
        """
        ctx = cls(max_tokens=max_tokens)
        
        if user_profile:
            profile_text = "\n".join([f"- {k}: {v}" for k, v in user_profile.items()])
            ctx.add_custom(
                "user_profile",
                f"用户信息:\n{profile_text}",
                priority=ContextPriority.HIGH
            )
        
        if order_history:
            orders_text = "\n".join([
                f"- 订单 {o.get('id', '?')}: {o.get('status', 'unknown')}"
                for o in order_history[-10:]  # 最近10个订单
            ])
            ctx.add_custom(
                "order_history",
                f"订单历史:\n{orders_text}",
                priority=ContextPriority.MEDIUM
            )
        
        if knowledge_base:
            ctx.add_rag_results(knowledge_base)
        
        return ctx
    
    @classmethod
    def for_document_editor(
        cls,
        document_metadata: Optional[Dict] = None,
        current_selection: Optional[str] = None,
        writing_style: Optional[str] = None,
        max_tokens: int = 8000,
    ) -> "ContextManager":
        """
        文档编辑器的快速集成模板
        
        Args:
            document_metadata: 文档元数据（标题、作者、标签等）
            current_selection: 当前选中的文本
            writing_style: 写作风格偏好
            max_tokens: Token 限制
        
        Returns:
            配置好的 ContextManager 实例
        
        示例:
            ```python
            ctx = ContextManager.for_document_editor(
                document_metadata={"title": "产品文档", "author": "张三"},
                current_selection="这段文字需要润色",
                writing_style="正式、专业"
            )
            ```
        """
        ctx = cls(max_tokens=max_tokens)
        
        if document_metadata:
            metadata_text = "\n".join([f"- {k}: {v}" for k, v in document_metadata.items()])
            ctx.add_custom(
                "document_metadata",
                f"文档信息:\n{metadata_text}",
                priority=ContextPriority.MEDIUM
            )
        
        if current_selection:
            ctx.add_custom(
                "current_selection",
                f"选中的内容:\n{current_selection}",
                priority=ContextPriority.HIGH
            )
        
        if writing_style:
            ctx.add_user_preferences({"writing_style": writing_style})
        
        return ctx

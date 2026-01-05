# -*- coding: utf-8 -*-
"""
智能工具编排器 - Tool Orchestrator

模仿 Cursor 的工具选择和编排能力：
1. 智能工具选择：根据任务自动选择最合适的工具
2. 工具组合：多个工具的组合使用
3. 工具依赖管理：处理工具之间的依赖关系
4. 结果聚合：合并多个工具的结果
5. 失败恢复：工具失败时的备选方案
"""
from typing import List, Dict, Any, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
import asyncio
import inspect
import re


def get_tool_name(tool: Any) -> str:
    """获取工具名称，兼容函数和 StructuredTool"""
    # StructuredTool 有 .name 属性
    if hasattr(tool, 'name'):
        return tool.name
    # 普通函数使用 __name__
    if hasattr(tool, '__name__'):
        return tool.__name__
    # 其他情况
    return str(tool)


def get_tool_doc(tool: Any) -> str:
    """获取工具文档，兼容函数和 StructuredTool"""
    # StructuredTool 有 .description 属性
    if hasattr(tool, 'description'):
        return tool.description or ""
    # 普通函数使用 __doc__
    if hasattr(tool, '__doc__'):
        return tool.__doc__ or ""
    return ""


class ToolCategory(Enum):
    """工具分类"""
    FILE_SYSTEM = "file_system"      # 文件操作
    SHELL = "shell"                   # Shell 命令
    WEB = "web"                       # 网络请求
    CODE = "code"                     # 代码执行
    SEARCH = "search"                 # 搜索检索
    SYSTEM = "system"                 # 系统信息
    DATA = "data"                     # 数据处理
    COMMUNICATION = "communication"   # 通信


@dataclass
class ToolMetadata:
    """
    工具元数据
    
    描述工具的能力和特性
    """
    name: str
    description: str
    category: ToolCategory
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_type: str = "text"
    
    # 能力标签
    capabilities: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    
    # 依赖和冲突
    requires: List[str] = field(default_factory=list)  # 依赖的其他工具
    conflicts: List[str] = field(default_factory=list)  # 冲突的工具
    
    # 执行特性
    is_async: bool = False
    is_dangerous: bool = False       # 需要确认
    timeout: int = 60                # 超时秒数
    retry_count: int = 1             # 重试次数
    
    # 备选方案
    fallback_tools: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "input_schema": self.input_schema,
            "capabilities": self.capabilities,
            "keywords": self.keywords,
            "is_dangerous": self.is_dangerous,
        }


@dataclass
class ToolSelection:
    """
    工具选择结果
    """
    tool_name: str
    confidence: float
    reason: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    fallbacks: List[str] = field(default_factory=list)


@dataclass
class OrchestrationPlan:
    """
    编排计划
    
    描述如何组合使用多个工具
    """
    steps: List[Dict[str, Any]]
    dependencies: Dict[str, List[str]]  # tool -> depends on
    parallel_groups: List[List[str]]    # 可以并行执行的工具组
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": self.steps,
            "dependencies": self.dependencies,
            "parallel_groups": self.parallel_groups,
        }


class ToolOrchestrator:
    """
    智能工具编排器
    
    核心能力：
    1. 工具注册和管理
    2. 智能工具选择
    3. 多工具编排
    4. 执行和结果聚合
    """
    
    # 工具能力关键词映射
    CAPABILITY_KEYWORDS = {
        "file_read": ["读取", "查看", "打开", "文件内容", "read", "view", "open", "cat"],
        "file_write": ["写入", "保存", "创建文件", "write", "save", "create"],
        "file_list": ["列出", "目录", "文件列表", "ls", "list", "dir"],
        "shell": ["执行命令", "运行", "shell", "bash", "命令行", "terminal"],
        "web": ["网页", "url", "http", "fetch", "下载", "网络"],
        "search": ["搜索", "查找", "检索", "search", "find", "query"],
        "code": ["代码", "python", "计算", "执行代码", "脚本"],
        "process": ["进程", "运行中", "ps", "process"],
        "system": ["系统", "环境", "信息", "status"],
    }
    
    def __init__(self, llm_client=None):
        """
        初始化工具编排器
        
        Args:
            llm_client: LLM 客户端（用于智能选择）
        """
        self.llm = llm_client
        self.tools: Dict[str, Callable] = {}
        self.metadata: Dict[str, ToolMetadata] = {}
        
        logger.info("ToolOrchestrator initialized")
    
    def register(
        self,
        tool: Callable,
        metadata: Optional[ToolMetadata] = None,
    ) -> None:
        """
        注册工具
        
        Args:
            tool: 工具函数或 StructuredTool
            metadata: 工具元数据（可选，会自动推断）
        """
        name = get_tool_name(tool)
        
        if metadata is None:
            metadata = self._infer_metadata(tool)
        
        self.tools[name] = tool
        self.metadata[name] = metadata
        
        logger.debug(f"Registered tool: {name}")
    
    def register_many(self, tools: List[Callable]) -> int:
        """批量注册工具"""
        count = 0
        for tool in tools:
            try:
                self.register(tool)
                count += 1
            except Exception as e:
                logger.error(f"Failed to register {get_tool_name(tool)}: {e}")
        return count
    
    def _infer_metadata(self, tool: Callable) -> ToolMetadata:
        """从工具函数推断元数据"""
        name = get_tool_name(tool)
        doc = get_tool_doc(tool)
        
        # 推断分类
        category = self._infer_category(name, doc)
        
        # 提取关键词
        keywords = self._extract_keywords(name, doc)
        
        # 提取能力
        capabilities = self._extract_capabilities(name, doc)
        
        # 检查是否异步 - 兼容 StructuredTool
        is_async = False
        if hasattr(tool, 'coroutine') and tool.coroutine is not None:
            is_async = True
        elif hasattr(tool, 'func') and asyncio.iscoroutinefunction(getattr(tool, 'func', None)):
            is_async = True
        elif callable(tool) and asyncio.iscoroutinefunction(tool):
            is_async = True
        
        # 检查是否危险
        is_dangerous = any(kw in name.lower() for kw in ["delete", "remove", "execute", "write"])
        
        # 提取输入参数 - 兼容 StructuredTool
        input_schema = {}
        try:
            if hasattr(tool, 'args_schema') and tool.args_schema is not None:
                # StructuredTool 有 args_schema
                for field_name, field_info in tool.args_schema.model_fields.items():
                    input_schema[field_name] = {
                        "type": str(field_info.annotation) if hasattr(field_info, 'annotation') else "any",
                        "required": field_info.is_required() if hasattr(field_info, 'is_required') else True,
                    }
            else:
                # 普通函数
                sig = inspect.signature(tool)
                for param_name, param in sig.parameters.items():
                    if param_name in ["self", "cls"]:
                        continue
                    input_schema[param_name] = {
                        "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "any",
                        "required": param.default == inspect.Parameter.empty,
                    }
        except Exception:
            pass  # 如果无法解析，使用空 schema
        
        return ToolMetadata(
            name=name,
            description=doc.split("\n")[0] if doc else name,
            category=category,
            input_schema=input_schema,
            capabilities=capabilities,
            keywords=keywords,
            is_async=is_async,
            is_dangerous=is_dangerous,
        )
    
    def _infer_category(self, name: str, doc: str) -> ToolCategory:
        """推断工具分类"""
        text = (name + " " + doc).lower()
        
        if any(kw in text for kw in ["file", "read", "write", "directory"]):
            return ToolCategory.FILE_SYSTEM
        if any(kw in text for kw in ["shell", "execute", "command", "bash"]):
            return ToolCategory.SHELL
        if any(kw in text for kw in ["http", "url", "web", "fetch"]):
            return ToolCategory.WEB
        if any(kw in text for kw in ["code", "python", "run", "script"]):
            return ToolCategory.CODE
        if any(kw in text for kw in ["search", "find", "query", "retrieve"]):
            return ToolCategory.SEARCH
        if any(kw in text for kw in ["system", "process", "env"]):
            return ToolCategory.SYSTEM
        
        return ToolCategory.DATA
    
    def _extract_keywords(self, name: str, doc: str) -> List[str]:
        """提取关键词"""
        keywords = []
        
        # 从名称提取
        words = re.split(r'[_\-\s]', name.lower())
        keywords.extend(words)
        
        # 从文档提取
        if doc:
            doc_words = re.findall(r'\b\w+\b', doc.lower())
            keywords.extend(doc_words[:10])
        
        return list(set(keywords))
    
    def _extract_capabilities(self, name: str, doc: str) -> List[str]:
        """提取能力标签"""
        capabilities = []
        text = (name + " " + doc).lower()
        
        for cap, keywords in self.CAPABILITY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                capabilities.append(cap)
        
        return capabilities
    
    async def select_tools(
        self,
        task: str,
        max_tools: int = 3,
        required_categories: Optional[Set[ToolCategory]] = None,
    ) -> List[ToolSelection]:
        """
        为任务选择合适的工具
        
        Args:
            task: 任务描述
            max_tools: 最多选择几个工具
            required_categories: 必须包含的分类
        
        Returns:
            工具选择列表，按置信度排序
        """
        logger.info(f"Selecting tools for: {task[:50]}...")
        
        # 1. 关键词匹配快速筛选
        candidates = self._keyword_match(task)
        
        # 2. 如果有 LLM，使用智能选择
        if self.llm and len(candidates) > max_tools:
            candidates = await self._llm_select(task, candidates, max_tools)
        
        # 3. 过滤分类
        if required_categories:
            candidates = [c for c in candidates 
                         if self.metadata[c.tool_name].category in required_categories]
        
        # 4. 排序并返回
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        return candidates[:max_tools]
    
    def _keyword_match(self, task: str) -> List[ToolSelection]:
        """基于关键词的工具匹配"""
        task_lower = task.lower()
        selections = []
        
        for name, meta in self.metadata.items():
            score = 0
            matched_keywords = []
            
            # 检查关键词匹配
            for keyword in meta.keywords:
                if keyword in task_lower:
                    score += 1
                    matched_keywords.append(keyword)
            
            # 检查能力匹配
            for cap in meta.capabilities:
                cap_keywords = self.CAPABILITY_KEYWORDS.get(cap, [])
                for kw in cap_keywords:
                    if kw in task_lower:
                        score += 2
                        matched_keywords.append(kw)
            
            if score > 0:
                confidence = min(score / 5, 1.0)
                selections.append(ToolSelection(
                    tool_name=name,
                    confidence=confidence,
                    reason=f"匹配关键词: {', '.join(matched_keywords[:3])}",
                    fallbacks=meta.fallback_tools,
                ))
        
        return selections
    
    async def _llm_select(
        self,
        task: str,
        candidates: List[ToolSelection],
        max_tools: int,
    ) -> List[ToolSelection]:
        """使用 LLM 智能选择工具"""
        # 构建工具描述
        tool_descriptions = []
        for sel in candidates:
            meta = self.metadata[sel.tool_name]
            tool_descriptions.append(f"- {sel.tool_name}: {meta.description}")
        
        prompt = f"""为以下任务选择最合适的工具（最多 {max_tools} 个）：

任务: {task}

可用工具:
{chr(10).join(tool_descriptions)}

请返回 JSON 数组，包含工具名和理由:
```json
[
  {{"tool": "工具名", "reason": "选择理由", "confidence": 0.9}},
  ...
]
```"""
        
        try:
            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            
            # 解析响应
            import json
            json_match = re.search(r'```json\s*(\[.*?\])\s*```', response, re.DOTALL)
            if json_match:
                selections_data = json.loads(json_match.group(1))
            else:
                selections_data = json.loads(response)
            
            # 转换为 ToolSelection
            result = []
            for item in selections_data[:max_tools]:
                tool_name = item.get("tool", "")
                if tool_name in self.tools:
                    result.append(ToolSelection(
                        tool_name=tool_name,
                        confidence=item.get("confidence", 0.8),
                        reason=item.get("reason", ""),
                        fallbacks=self.metadata[tool_name].fallback_tools,
                    ))
            
            return result if result else candidates[:max_tools]
            
        except Exception as e:
            logger.error(f"LLM tool selection failed: {e}")
            return candidates[:max_tools]
    
    async def create_orchestration_plan(
        self,
        task: str,
        selected_tools: List[ToolSelection],
    ) -> OrchestrationPlan:
        """
        创建工具编排计划
        
        决定工具的执行顺序和依赖关系
        """
        steps = []
        dependencies = {}
        parallel_groups = []
        
        # 分析依赖关系
        for i, sel in enumerate(selected_tools):
            meta = self.metadata[sel.tool_name]
            
            step = {
                "step": i + 1,
                "tool": sel.tool_name,
                "reason": sel.reason,
                "arguments": sel.arguments,
            }
            steps.append(step)
            
            # 检查依赖
            deps = []
            for req in meta.requires:
                if req in [s.tool_name for s in selected_tools[:i]]:
                    deps.append(req)
            dependencies[sel.tool_name] = deps
        
        # 识别可并行的工具
        no_deps = [s.tool_name for s in selected_tools 
                   if not dependencies.get(s.tool_name, [])]
        if len(no_deps) > 1:
            parallel_groups.append(no_deps)
        
        return OrchestrationPlan(
            steps=steps,
            dependencies=dependencies,
            parallel_groups=parallel_groups,
        )
    
    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: Optional[int] = None,
    ) -> Tuple[bool, Any]:
        """
        执行工具
        
        Returns:
            (成功, 结果或错误)
        """
        if tool_name not in self.tools:
            return False, f"工具 '{tool_name}' 不存在"
        
        tool = self.tools[tool_name]
        meta = self.metadata[tool_name]
        timeout = timeout or meta.timeout
        
        try:
            # 检查是否是 StructuredTool (LangChain 工具)
            if hasattr(tool, 'invoke'):
                # StructuredTool 使用 invoke/ainvoke
                if hasattr(tool, 'ainvoke'):
                    result = await asyncio.wait_for(
                        tool.ainvoke(arguments),
                        timeout=timeout,
                    )
                else:
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: tool.invoke(arguments)),
                        timeout=timeout,
                    )
            elif meta.is_async:
                result = await asyncio.wait_for(
                    tool(**arguments),
                    timeout=timeout,
                )
            else:
                # 在线程池中执行同步函数
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: tool(**arguments)),
                    timeout=timeout,
                )
            
            return True, result
            
        except asyncio.TimeoutError:
            # 尝试备选工具
            for fallback in meta.fallback_tools:
                if fallback in self.tools:
                    logger.info(f"Trying fallback tool: {fallback}")
                    return await self.execute(fallback, arguments, timeout)
            
            return False, f"工具 '{tool_name}' 执行超时"
            
        except Exception as e:
            return False, str(e)
    
    async def execute_plan(
        self,
        plan: OrchestrationPlan,
    ) -> Dict[str, Any]:
        """
        执行编排计划
        
        Returns:
            各工具的执行结果
        """
        results = {}
        
        # 先执行可并行的
        for group in plan.parallel_groups:
            tasks = []
            for tool_name in group:
                step = next((s for s in plan.steps if s["tool"] == tool_name), None)
                if step:
                    tasks.append(self.execute(tool_name, step.get("arguments", {})))
            
            group_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for tool_name, result in zip(group, group_results):
                if isinstance(result, Exception):
                    results[tool_name] = {"success": False, "error": str(result)}
                else:
                    success, output = result
                    results[tool_name] = {"success": success, "output": output}
        
        # 执行剩余步骤
        for step in plan.steps:
            tool_name = step["tool"]
            if tool_name in results:
                continue
            
            # 检查依赖
            deps = plan.dependencies.get(tool_name, [])
            deps_ok = all(results.get(d, {}).get("success", False) for d in deps)
            
            if not deps_ok:
                results[tool_name] = {"success": False, "error": "依赖未满足"}
                continue
            
            success, output = await self.execute(tool_name, step.get("arguments", {}))
            results[tool_name] = {"success": success, "output": output}
        
        return results
    
    def get_tools_summary(self) -> str:
        """获取所有工具的摘要"""
        lines = ["## 可用工具\n"]
        
        by_category = {}
        for name, meta in self.metadata.items():
            cat = meta.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(meta)
        
        for cat, tools in by_category.items():
            lines.append(f"### {cat}")
            for tool in tools:
                danger = "⚠️" if tool.is_dangerous else ""
                lines.append(f"- `{tool.name}` {danger}: {tool.description}")
            lines.append("")
        
        return "\n".join(lines)


# 全局实例
_tool_orchestrator: Optional[ToolOrchestrator] = None


def get_tool_orchestrator(llm_client=None) -> ToolOrchestrator:
    """获取工具编排器实例"""
    global _tool_orchestrator
    if _tool_orchestrator is None:
        _tool_orchestrator = ToolOrchestrator(llm_client)
    return _tool_orchestrator


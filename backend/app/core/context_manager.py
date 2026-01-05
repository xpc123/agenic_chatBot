# -*- coding: utf-8 -*-
"""
上下文工程 - Context Engineering

模仿 Cursor 的上下文管理能力：
1. 统一上下文构建：将多源信息整合为结构化上下文
2. 优先级排序：根据相关性对上下文排序
3. Token 预算管理：在限制内最大化信息量
4. 动态压缩：智能压缩过长内容
5. 引用追踪：记录信息来源用于引用

这是 Cursor 能够理解复杂项目的关键能力！
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from loguru import logger
import json
import tiktoken


class ContextSource(Enum):
    """上下文来源"""
    USER_MESSAGE = "user_message"        # 用户消息
    CONVERSATION = "conversation"        # 对话历史
    RAG = "rag"                          # 知识库检索
    FILE = "file"                        # 文件内容
    MEMORY = "memory"                    # 长期记忆
    TOOL_RESULT = "tool_result"          # 工具执行结果
    SKILL = "skill"                      # 技能指令
    SYSTEM = "system"                    # 系统信息


class ContextPriority(Enum):
    """上下文优先级"""
    CRITICAL = 1    # 必须包含
    HIGH = 2        # 高优先级
    MEDIUM = 3      # 中优先级
    LOW = 4         # 低优先级


@dataclass
class ContextBlock:
    """
    上下文块
    
    表示一个独立的上下文单元
    """
    id: str
    source: ContextSource
    content: str
    priority: ContextPriority = ContextPriority.MEDIUM
    
    # 元信息
    title: str = ""
    citation: str = ""              # 引用标识
    relevance_score: float = 0.0    # 相关性分数
    
    # Token 信息
    token_count: int = 0
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    
    # 额外数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_formatted(self) -> str:
        """格式化为可读文本"""
        lines = []
        if self.title:
            lines.append(f"### {self.title}")
        if self.citation:
            lines.append(f"*来源: {self.citation}*")
        lines.append(self.content)
        return "\n".join(lines)


@dataclass 
class ContextWindow:
    """
    上下文窗口
    
    管理 Token 预算和内容
    """
    max_tokens: int
    blocks: List[ContextBlock] = field(default_factory=list)
    
    @property
    def used_tokens(self) -> int:
        return sum(b.token_count for b in self.blocks)
    
    @property
    def remaining_tokens(self) -> int:
        return self.max_tokens - self.used_tokens
    
    @property
    def usage_percent(self) -> float:
        return (self.used_tokens / self.max_tokens) * 100 if self.max_tokens > 0 else 0


class ContextManager:
    """
    上下文管理器
    
    核心能力：
    1. 收集多源上下文
    2. 优先级排序
    3. Token 预算管理
    4. 智能压缩
    5. 统一格式输出
    """
    
    # 默认配置
    DEFAULT_MAX_TOKENS = 8000
    COMPRESSION_THRESHOLD = 0.9  # 90% 时开始压缩
    
    # 各来源的默认优先级
    SOURCE_PRIORITIES = {
        ContextSource.USER_MESSAGE: ContextPriority.CRITICAL,
        ContextSource.SKILL: ContextPriority.HIGH,
        ContextSource.RAG: ContextPriority.HIGH,
        ContextSource.FILE: ContextPriority.HIGH,
        ContextSource.CONVERSATION: ContextPriority.MEDIUM,
        ContextSource.MEMORY: ContextPriority.MEDIUM,
        ContextSource.TOOL_RESULT: ContextPriority.MEDIUM,
        ContextSource.SYSTEM: ContextPriority.LOW,
    }
    
    def __init__(
        self,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        model: str = "gpt-4",
    ):
        """
        初始化上下文管理器
        
        Args:
            max_tokens: 最大 Token 数
            model: 用于 Token 计算的模型
        """
        self.max_tokens = max_tokens
        self.model = model
        
        # Token 计数器
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except Exception:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        
        # 上下文收集器
        self.blocks: List[ContextBlock] = []
        
        logger.info(f"ContextManager initialized with {max_tokens} tokens")
    
    def count_tokens(self, text: str) -> int:
        """计算 Token 数"""
        try:
            return len(self.encoding.encode(text))
        except Exception:
            # 降级：估算
            return len(text) // 4
    
    def add(
        self,
        content: str,
        source: ContextSource,
        priority: Optional[ContextPriority] = None,
        title: str = "",
        citation: str = "",
        relevance_score: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContextBlock:
        """
        添加上下文块
        
        Args:
            content: 内容
            source: 来源
            priority: 优先级（None 则使用来源默认值）
            title: 标题
            citation: 引用标识
            relevance_score: 相关性分数
            metadata: 额外元数据
        
        Returns:
            创建的上下文块
        """
        if priority is None:
            priority = self.SOURCE_PRIORITIES.get(source, ContextPriority.MEDIUM)
        
        block = ContextBlock(
            id=f"{source.value}_{len(self.blocks)}",
            source=source,
            content=content,
            priority=priority,
            title=title,
            citation=citation,
            relevance_score=relevance_score,
            token_count=self.count_tokens(content),
            metadata=metadata or {},
        )
        
        self.blocks.append(block)
        logger.debug(f"Added context block: {block.id} ({block.token_count} tokens)")
        
        return block
    
    def add_user_message(self, message: str) -> ContextBlock:
        """添加用户消息"""
        return self.add(
            content=message,
            source=ContextSource.USER_MESSAGE,
            title="用户消息",
            priority=ContextPriority.CRITICAL,
        )
    
    def add_conversation_history(
        self,
        messages: List[Dict[str, str]],
        max_messages: int = 10,
    ) -> List[ContextBlock]:
        """添加对话历史"""
        blocks = []
        
        # 取最近的消息
        recent = messages[-max_messages:] if len(messages) > max_messages else messages
        
        for i, msg in enumerate(recent):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            block = self.add(
                content=f"{role}: {content}",
                source=ContextSource.CONVERSATION,
                title=f"对话 #{len(messages) - len(recent) + i + 1}",
                priority=ContextPriority.MEDIUM,
                relevance_score=0.5 + (i * 0.05),  # 越新越相关
            )
            blocks.append(block)
        
        return blocks
    
    def add_rag_results(
        self,
        results: List[Dict[str, Any]],
        max_results: int = 5,
    ) -> List[ContextBlock]:
        """添加 RAG 检索结果"""
        blocks = []
        
        for i, result in enumerate(results[:max_results]):
            content = result.get("content", "")
            source = result.get("source", result.get("metadata", {}).get("source", "未知来源"))
            score = result.get("score", 0.0)
            
            block = self.add(
                content=content,
                source=ContextSource.RAG,
                title=f"知识库结果 #{i+1}",
                citation=source,
                relevance_score=score,
                priority=ContextPriority.HIGH,
                metadata=result.get("metadata", {}),
            )
            blocks.append(block)
        
        return blocks
    
    def add_file_content(
        self,
        path: str,
        content: str,
        relevance_score: float = 0.8,
    ) -> ContextBlock:
        """添加文件内容"""
        return self.add(
            content=content,
            source=ContextSource.FILE,
            title=f"文件: {path}",
            citation=path,
            relevance_score=relevance_score,
            priority=ContextPriority.HIGH,
        )
    
    def add_skill_instructions(
        self,
        skill_name: str,
        instructions: str,
        examples: Optional[List[str]] = None,
    ) -> ContextBlock:
        """添加技能指令"""
        content_parts = [instructions]
        if examples:
            content_parts.append("\n**示例:**")
            for ex in examples[:3]:
                content_parts.append(f"- {ex}")
        
        return self.add(
            content="\n".join(content_parts),
            source=ContextSource.SKILL,
            title=f"技能: {skill_name}",
            priority=ContextPriority.HIGH,
        )
    
    def add_memory(
        self,
        memories: List[Dict[str, Any]],
    ) -> List[ContextBlock]:
        """添加长期记忆"""
        blocks = []
        
        for mem in memories:
            content = mem.get("content", "")
            score = mem.get("score", 0.5)
            
            block = self.add(
                content=content,
                source=ContextSource.MEMORY,
                title="相关记忆",
                relevance_score=score,
                priority=ContextPriority.MEDIUM,
            )
            blocks.append(block)
        
        return blocks
    
    def add_tool_result(
        self,
        tool_name: str,
        result: str,
    ) -> ContextBlock:
        """添加工具执行结果"""
        return self.add(
            content=result,
            source=ContextSource.TOOL_RESULT,
            title=f"工具结果: {tool_name}",
            priority=ContextPriority.MEDIUM,
        )
    
    def build(
        self,
        compress_if_needed: bool = True,
    ) -> str:
        """
        构建最终上下文
        
        Args:
            compress_if_needed: 超出预算时是否压缩
        
        Returns:
            格式化的上下文字符串
        """
        # 1. 按优先级和相关性排序
        sorted_blocks = sorted(
            self.blocks,
            key=lambda b: (b.priority.value, -b.relevance_score),
        )
        
        # 2. 选择在预算内的块
        selected = []
        used_tokens = 0
        
        for block in sorted_blocks:
            if used_tokens + block.token_count <= self.max_tokens:
                selected.append(block)
                used_tokens += block.token_count
            elif block.priority == ContextPriority.CRITICAL:
                # 必须包含的内容，尝试压缩
                if compress_if_needed:
                    compressed = self._compress_block(block, self.max_tokens - used_tokens)
                    if compressed:
                        selected.append(compressed)
                        used_tokens += compressed.token_count
        
        # 3. 按来源分组
        grouped = self._group_by_source(selected)
        
        # 4. 格式化输出
        output_parts = []
        
        for source, blocks in grouped.items():
            if not blocks:
                continue
            
            section_title = self._get_section_title(source)
            output_parts.append(f"## {section_title}\n")
            
            for block in blocks:
                output_parts.append(block.to_formatted())
                output_parts.append("")
        
        result = "\n".join(output_parts)
        
        logger.info(f"Built context: {used_tokens} tokens, {len(selected)} blocks")
        
        return result
    
    def _group_by_source(
        self,
        blocks: List[ContextBlock],
    ) -> Dict[ContextSource, List[ContextBlock]]:
        """按来源分组"""
        grouped = {}
        
        # 定义来源顺序
        source_order = [
            ContextSource.SKILL,
            ContextSource.RAG,
            ContextSource.FILE,
            ContextSource.MEMORY,
            ContextSource.CONVERSATION,
            ContextSource.TOOL_RESULT,
            ContextSource.SYSTEM,
        ]
        
        for source in source_order:
            grouped[source] = [b for b in blocks if b.source == source]
        
        return grouped
    
    def _get_section_title(self, source: ContextSource) -> str:
        """获取来源的章节标题"""
        titles = {
            ContextSource.SKILL: "📋 任务指令",
            ContextSource.RAG: "📚 知识库参考",
            ContextSource.FILE: "📄 相关文件",
            ContextSource.MEMORY: "💭 相关记忆",
            ContextSource.CONVERSATION: "💬 对话历史",
            ContextSource.TOOL_RESULT: "🔧 工具结果",
            ContextSource.SYSTEM: "ℹ️ 系统信息",
        }
        return titles.get(source, source.value)
    
    def _compress_block(
        self,
        block: ContextBlock,
        target_tokens: int,
    ) -> Optional[ContextBlock]:
        """压缩上下文块"""
        if target_tokens <= 50:
            return None
        
        content = block.content
        current_tokens = block.token_count
        
        # 简单截断
        if current_tokens > target_tokens:
            # 估算保留比例
            ratio = target_tokens / current_tokens
            keep_chars = int(len(content) * ratio * 0.9)  # 留10%余量
            
            compressed_content = content[:keep_chars] + "\n...(内容已压缩)"
            
            return ContextBlock(
                id=block.id + "_compressed",
                source=block.source,
                content=compressed_content,
                priority=block.priority,
                title=block.title,
                citation=block.citation,
                relevance_score=block.relevance_score,
                token_count=self.count_tokens(compressed_content),
                metadata=block.metadata,
            )
        
        return block
    
    def get_citations(self) -> List[Dict[str, str]]:
        """获取所有引用"""
        citations = []
        
        for block in self.blocks:
            if block.citation:
                citations.append({
                    "id": block.id,
                    "source": block.source.value,
                    "citation": block.citation,
                })
        
        return citations
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        by_source = {}
        for block in self.blocks:
            source = block.source.value
            if source not in by_source:
                by_source[source] = {"count": 0, "tokens": 0}
            by_source[source]["count"] += 1
            by_source[source]["tokens"] += block.token_count
        
        return {
            "total_blocks": len(self.blocks),
            "total_tokens": sum(b.token_count for b in self.blocks),
            "max_tokens": self.max_tokens,
            "by_source": by_source,
        }
    
    def clear(self):
        """清除所有上下文"""
        self.blocks.clear()
        logger.debug("Context cleared")


# 便捷函数：快速构建上下文
def build_context(
    user_message: str,
    conversation: Optional[List[Dict[str, str]]] = None,
    rag_results: Optional[List[Dict[str, Any]]] = None,
    files: Optional[Dict[str, str]] = None,
    skill_instructions: Optional[str] = None,
    memories: Optional[List[Dict[str, Any]]] = None,
    max_tokens: int = 8000,
) -> str:
    """
    快速构建上下文
    
    Args:
        user_message: 用户消息
        conversation: 对话历史
        rag_results: RAG 检索结果
        files: 文件内容 {path: content}
        skill_instructions: 技能指令
        memories: 长期记忆
        max_tokens: 最大 Token 数
    
    Returns:
        格式化的上下文字符串
    """
    cm = ContextManager(max_tokens=max_tokens)
    
    # 添加技能指令
    if skill_instructions:
        cm.add_skill_instructions("当前任务", skill_instructions)
    
    # 添加 RAG 结果
    if rag_results:
        cm.add_rag_results(rag_results)
    
    # 添加文件内容
    if files:
        for path, content in files.items():
            cm.add_file_content(path, content)
    
    # 添加记忆
    if memories:
        cm.add_memory(memories)
    
    # 添加对话历史
    if conversation:
        cm.add_conversation_history(conversation)
    
    return cm.build()

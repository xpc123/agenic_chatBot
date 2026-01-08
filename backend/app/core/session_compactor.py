# -*- coding: utf-8 -*-
"""
会话压缩器 - Session Compactor

参考 OpenCode 的 compaction 机制实现：
1. 自动压缩 - 当上下文接近限制时自动触发
2. 摘要生成 - 将长对话压缩为摘要
3. 工具结果裁剪 - 精简旧的工具输出
4. 智能保留 - 保留重要信息，移除冗余
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger
import json
import tiktoken

from ..models.chat import ChatMessage, MessageRole
from ..config import settings


@dataclass
class CompactionResult:
    """压缩结果"""
    original_messages: int
    compacted_messages: int
    original_tokens: int
    compacted_tokens: int
    summary: Optional[str] = None
    preserved_count: int = 0
    pruned_count: int = 0
    
    @property
    def compression_ratio(self) -> float:
        if self.original_tokens == 0:
            return 0.0
        return 1 - (self.compacted_tokens / self.original_tokens)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_messages": self.original_messages,
            "compacted_messages": self.compacted_messages,
            "original_tokens": self.original_tokens,
            "compacted_tokens": self.compacted_tokens,
            "compression_ratio": f"{self.compression_ratio:.1%}",
            "summary_length": len(self.summary) if self.summary else 0,
            "preserved_count": self.preserved_count,
            "pruned_count": self.pruned_count,
        }


@dataclass
class CompactionConfig:
    """压缩配置"""
    # 自动压缩阈值（Token 数）
    auto_compact_threshold: int = 6000
    # 压缩后目标 Token 数
    target_tokens: int = 3000
    # 保留最近 N 条消息不压缩
    preserve_recent: int = 4
    # 是否裁剪旧的工具输出
    prune_tool_outputs: bool = True
    # 工具输出最大长度
    max_tool_output_length: int = 500
    # 是否生成摘要
    generate_summary: bool = True
    # 摘要最大长度
    max_summary_length: int = 1000


class SessionCompactor:
    """
    会话压缩器
    
    功能:
    1. 自动检测是否需要压缩
    2. 生成对话摘要
    3. 裁剪工具输出
    4. 智能保留重要消息
    
    使用示例:
    ```python
    compactor = SessionCompactor(llm_client)
    
    # 检查是否需要压缩
    if compactor.should_compact(messages):
        result = await compactor.compact(messages)
        print(f"压缩率: {result.compression_ratio:.1%}")
    ```
    """
    
    def __init__(
        self,
        llm_client=None,
        config: Optional[CompactionConfig] = None,
    ):
        """
        初始化压缩器
        
        Args:
            llm_client: LLM 客户端（用于生成摘要）
            config: 压缩配置
        """
        self.llm = llm_client
        self.config = config or CompactionConfig()
        
        # Token 计数器
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None
        
        logger.info("SessionCompactor initialized")
    
    def count_tokens(self, text: str) -> int:
        """计算文本的 Token 数"""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        # 粗略估计：每个字符约 0.3 个 token（中文），0.25（英文）
        return int(len(text) * 0.3)
    
    def count_messages_tokens(self, messages: List[ChatMessage]) -> int:
        """计算消息列表的总 Token 数"""
        total = 0
        for msg in messages:
            total += self.count_tokens(msg.content or "")
            if msg.metadata:
                total += self.count_tokens(json.dumps(msg.metadata, ensure_ascii=False))
        return total
    
    def should_compact(self, messages: List[ChatMessage]) -> bool:
        """
        检查是否需要压缩
        
        Args:
            messages: 消息列表
        
        Returns:
            是否需要压缩
        """
        if len(messages) < self.config.preserve_recent + 2:
            return False
        
        total_tokens = self.count_messages_tokens(messages)
        return total_tokens > self.config.auto_compact_threshold
    
    async def compact(
        self,
        messages: List[ChatMessage],
        force: bool = False,
    ) -> Tuple[List[ChatMessage], CompactionResult]:
        """
        压缩消息列表
        
        Args:
            messages: 原始消息列表
            force: 是否强制压缩
        
        Returns:
            (压缩后的消息列表, 压缩结果)
        """
        original_tokens = self.count_messages_tokens(messages)
        original_count = len(messages)
        
        if not force and not self.should_compact(messages):
            return messages, CompactionResult(
                original_messages=original_count,
                compacted_messages=original_count,
                original_tokens=original_tokens,
                compacted_tokens=original_tokens,
            )
        
        logger.info(f"Compacting session: {original_count} messages, {original_tokens} tokens")
        
        # 分离保留的消息和需要压缩的消息
        preserve_count = self.config.preserve_recent
        messages_to_compact = messages[:-preserve_count] if preserve_count > 0 else messages
        preserved_messages = messages[-preserve_count:] if preserve_count > 0 else []
        
        # 1. 裁剪工具输出
        pruned_count = 0
        if self.config.prune_tool_outputs:
            messages_to_compact, pruned_count = self._prune_tool_outputs(messages_to_compact)
        
        # 2. 生成摘要
        summary = None
        if self.config.generate_summary and messages_to_compact:
            summary = await self._generate_summary(messages_to_compact)
        
        # 3. 构建压缩后的消息列表
        compacted_messages = []
        
        # 添加摘要消息
        if summary:
            summary_message = ChatMessage(
                role=MessageRole.SYSTEM,
                content=f"[会话摘要]\n{summary}",
                timestamp=datetime.now(),
                metadata={"type": "compaction_summary", "original_count": len(messages_to_compact)},
            )
            compacted_messages.append(summary_message)
        
        # 添加保留的消息
        compacted_messages.extend(preserved_messages)
        
        compacted_tokens = self.count_messages_tokens(compacted_messages)
        
        result = CompactionResult(
            original_messages=original_count,
            compacted_messages=len(compacted_messages),
            original_tokens=original_tokens,
            compacted_tokens=compacted_tokens,
            summary=summary,
            preserved_count=len(preserved_messages),
            pruned_count=pruned_count,
        )
        
        logger.info(f"Compaction complete: {result.compression_ratio:.1%} reduction")
        
        return compacted_messages, result
    
    def _prune_tool_outputs(
        self,
        messages: List[ChatMessage],
    ) -> Tuple[List[ChatMessage], int]:
        """
        裁剪工具输出
        
        将过长的工具输出截断
        
        Args:
            messages: 消息列表
        
        Returns:
            (裁剪后的消息, 裁剪数量)
        """
        pruned_count = 0
        pruned_messages = []
        
        for msg in messages:
            # 检查是否是工具结果
            is_tool_result = (
                msg.metadata and 
                msg.metadata.get("type") in ["tool_result", "tool_output"]
            )
            
            if is_tool_result and msg.content:
                original_length = len(msg.content)
                max_length = self.config.max_tool_output_length
                
                if original_length > max_length:
                    # 截断内容
                    truncated_content = msg.content[:max_length]
                    truncated_content += f"\n\n... [输出已截断，原始长度: {original_length} 字符]"
                    
                    # 创建新消息
                    pruned_msg = ChatMessage(
                        role=msg.role,
                        content=truncated_content,
                        timestamp=msg.timestamp,
                        metadata={
                            **(msg.metadata or {}),
                            "truncated": True,
                            "original_length": original_length,
                        },
                    )
                    pruned_messages.append(pruned_msg)
                    pruned_count += 1
                    continue
            
            pruned_messages.append(msg)
        
        return pruned_messages, pruned_count
    
    async def _generate_summary(
        self,
        messages: List[ChatMessage],
    ) -> Optional[str]:
        """
        生成对话摘要
        
        Args:
            messages: 要摘要的消息列表
        
        Returns:
            摘要文本
        """
        if not self.llm:
            # 没有 LLM，使用简单摘要
            return self._simple_summary(messages)
        
        try:
            # 构建对话文本
            conversation_parts = []
            for msg in messages:
                role = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
                content = msg.content or ""
                
                # 截断过长的内容
                if len(content) > 500:
                    content = content[:500] + "..."
                
                conversation_parts.append(f"{role}: {content}")
            
            conversation_text = "\n".join(conversation_parts)
            
            # 截断总长度
            if len(conversation_text) > 5000:
                conversation_text = conversation_text[:5000] + "\n..."
            
            summary_prompt = f"""请将以下对话内容压缩为简洁的摘要。

要求：
1. 保留关键信息和决策
2. 保留提到的文件名、路径、代码位置
3. 保留用户的主要请求和 AI 的主要回答
4. 使用简洁的语言，控制在 {self.config.max_summary_length} 字符以内
5. 使用项目符号格式

对话内容：
{conversation_text}

摘要："""

            # 调用 LLM
            response = await self.llm.chat_completion([
                {"role": "system", "content": "你是一个对话摘要助手。请生成简洁、信息丰富的摘要。"},
                {"role": "user", "content": summary_prompt}
            ])
            
            summary = response.strip() if isinstance(response, str) else str(response)
            
            # 确保不超过最大长度
            if len(summary) > self.config.max_summary_length:
                summary = summary[:self.config.max_summary_length] + "..."
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return self._simple_summary(messages)
    
    def _simple_summary(self, messages: List[ChatMessage]) -> str:
        """
        简单摘要（不使用 LLM）
        
        Args:
            messages: 消息列表
        
        Returns:
            简单摘要
        """
        user_messages = [m for m in messages if m.role == MessageRole.USER]
        assistant_messages = [m for m in messages if m.role == MessageRole.ASSISTANT]
        
        summary_parts = []
        
        # 用户请求摘要
        if user_messages:
            summary_parts.append("用户请求:")
            for msg in user_messages[:3]:
                content = (msg.content or "")[:100]
                if len(msg.content or "") > 100:
                    content += "..."
                summary_parts.append(f"  - {content}")
            if len(user_messages) > 3:
                summary_parts.append(f"  - ... 还有 {len(user_messages) - 3} 条消息")
        
        # 工具使用统计
        tool_calls = [m for m in messages if m.metadata and m.metadata.get("type") == "tool_call"]
        if tool_calls:
            tool_names = set()
            for tc in tool_calls:
                if tc.metadata and tc.metadata.get("tool_name"):
                    tool_names.add(tc.metadata["tool_name"])
            summary_parts.append(f"\n使用的工具: {', '.join(tool_names)}")
        
        # 统计信息
        summary_parts.append(f"\n对话统计: {len(user_messages)} 条用户消息, {len(assistant_messages)} 条回复")
        
        return "\n".join(summary_parts)
    
    async def auto_compact_if_needed(
        self,
        messages: List[ChatMessage],
    ) -> Tuple[List[ChatMessage], Optional[CompactionResult]]:
        """
        自动压缩（如果需要）
        
        Args:
            messages: 消息列表
        
        Returns:
            (处理后的消息列表, 压缩结果或 None)
        """
        if self.should_compact(messages):
            return await self.compact(messages)
        return messages, None


# ==================== 单例管理 ====================

_compactor_instance: Optional[SessionCompactor] = None


def get_session_compactor(llm_client=None) -> SessionCompactor:
    """获取会话压缩器单例"""
    global _compactor_instance
    
    if _compactor_instance is None:
        _compactor_instance = SessionCompactor(llm_client)
    
    return _compactor_instance


def init_session_compactor(llm_client, config: Optional[CompactionConfig] = None) -> SessionCompactor:
    """初始化会话压缩器"""
    global _compactor_instance
    _compactor_instance = SessionCompactor(llm_client, config)
    return _compactor_instance


__all__ = [
    "SessionCompactor",
    "CompactionResult",
    "CompactionConfig",
    "get_session_compactor",
    "init_session_compactor",
]



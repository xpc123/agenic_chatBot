# -*- coding: utf-8 -*-
"""
记忆管理系统 - Memory

LangChain 1.0 架构说明:
- Agent 的会话状态由 checkpointer 自动管理
- 历史压缩由 SummarizationMiddleware 自动处理
- 本模块主要用于:
  1. 补充的会话历史管理
  2. 长期记忆存储
  3. 与 RAG 系统的集成
  4. 会话数据的持久化备份
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import json
import os

from ..models.chat import ChatMessage, ConversationHistory, MessageRole
from ..config import settings


class MemoryManager:
    """
    记忆管理器
    
    三种记忆类型:
    1. 短期记忆 (Short-term): 当前对话上下文（内存中）
    2. 长期记忆 (Long-term): 跨会话的持久化存储（文件/数据库）
    3. 知识记忆 (Knowledge): RAG 文档知识库（向量数据库）
    
    与 LangChain 1.0 Agent 的关系:
    - Agent 通过 checkpointer 管理会话状态（自动持久化）
    - SummarizationMiddleware 自动压缩过长的对话历史
    - 本类提供额外的记忆管理功能，作为 Agent 的补充
    """
    
    def __init__(self):
        self.memory_type = settings.MEMORY_TYPE
        self.window_size = settings.MEMORY_WINDOW_SIZE
        self.memory_dir = settings.LONG_TERM_MEMORY_DIR
        
        # 短期记忆缓存 (内存中)
        self.short_term_memory: Dict[str, List[ChatMessage]] = {}
        
        # 确保目录存在
        os.makedirs(self.memory_dir, exist_ok=True)
        
        logger.info(f"MemoryManager initialized with type: {self.memory_type}")
    
    async def get_conversation_history(
        self,
        session_id: str,
        max_messages: Optional[int] = None,
    ) -> List[ChatMessage]:
        """
        获取对话历史
        
        Args:
            session_id: 会话 ID
            max_messages: 最大消息数
        
        Returns:
            消息列表
        """
        if session_id not in self.short_term_memory:
            # 尝试从持久化存储加载
            self.short_term_memory[session_id] = await self._load_from_disk(session_id)
        
        messages = self.short_term_memory[session_id]
        
        if max_messages:
            return messages[-max_messages:]
        
        if self.memory_type == "buffer_window":
            return messages[-self.window_size:]
        
        return messages
    
    async def add_message(
        self,
        session_id: str,
        message: ChatMessage,
    ) -> None:
        """
        添加消息到记忆
        
        Args:
            session_id: 会话 ID
            message: 消息
        """
        if session_id not in self.short_term_memory:
            self.short_term_memory[session_id] = []
        
        self.short_term_memory[session_id].append(message)
        
        # 定期持久化
        if len(self.short_term_memory[session_id]) % 10 == 0:
            await self._save_to_disk(session_id)
        
        logger.debug(f"Message added to session {session_id}")
    
    async def get_relevant_long_term_memory(
        self,
        session_id: str,
        query: str,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        获取相关的长期记忆
        
        使用语义搜索找到历史对话中的相关信息
        
        Args:
            session_id: 会话 ID
            query: 查询文本
            top_k: 返回数量
        
        Returns:
            相关记忆列表
        """
        # TODO: 实现基于向量的语义搜索
        # 可以使用与 RAG 相同的向量数据库
        
        logger.debug(f"Retrieving long-term memory for: {query[:50]}")
        return []
    
    async def summarize_conversation(
        self,
        session_id: str,
    ) -> Optional[str]:
        """
        总结对话内容（备用方法）
        
        注意：在 LangChain 1.0 中，建议使用 SummarizationMiddleware
        此方法作为独立调用的备用选项
        
        Args:
            session_id: 会话 ID
        
        Returns:
            对话摘要
        """
        messages = await self.get_conversation_history(session_id)
        
        if len(messages) < 5:
            return None
        
        # 使用 LLM 生成摘要
        try:
            from ..llm.client import get_llm_client
            
            llm = get_llm_client()
            
            # 构建对话文本
            conversation_text = "\n".join([
                f"{msg.role.value}: {msg.content}"
                for msg in messages
            ])
            
            summary_prompt = f"""请总结以下对话的主要内容，保留关键信息：

{conversation_text}

总结:"""
            
            summary = await llm.chat_completion([
                {"role": "user", "content": summary_prompt}
            ])
            
            logger.info(f"Conversation summarized for session {session_id}")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to summarize conversation: {e}")
            return None
    
    async def clear_session(self, session_id: str) -> None:
        """
        清除会话记忆
        
        Args:
            session_id: 会话 ID
        """
        if session_id in self.short_term_memory:
            del self.short_term_memory[session_id]
        
        # 删除持久化文件
        file_path = self._get_session_file_path(session_id)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        logger.info(f"Session {session_id} cleared")
    
    async def _save_to_disk(self, session_id: str) -> None:
        """保存到磁盘"""
        messages = self.short_term_memory.get(session_id, [])
        
        if not messages:
            return
        
        file_path = self._get_session_file_path(session_id)
        
        conversation = ConversationHistory(
            session_id=session_id,
            messages=messages,
            updated_at=datetime.now(),
        )
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(conversation.model_dump(), f, ensure_ascii=False, indent=2, default=str)
            
            logger.debug(f"Session {session_id} saved to disk")
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    async def _load_from_disk(self, session_id: str) -> List[ChatMessage]:
        """从磁盘加载"""
        file_path = self._get_session_file_path(session_id)
        
        if not os.path.exists(file_path):
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            conversation = ConversationHistory(**data)
            
            logger.debug(f"Session {session_id} loaded from disk")
            return conversation.messages
            
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return []
    
    def _get_session_file_path(self, session_id: str) -> str:
        """获取会话文件路径"""
        return os.path.join(self.memory_dir, f"{session_id}.json")
    
    async def cleanup_old_sessions(self, days: int = 7) -> None:
        """
        清理旧会话
        
        Args:
            days: 保留天数
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        removed_count = 0
        
        for filename in os.listdir(self.memory_dir):
            file_path = os.path.join(self.memory_dir, filename)
            
            if os.path.isfile(file_path) and filename.endswith('.json'):
                mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                if mtime < cutoff_time:
                    os.remove(file_path)
                    removed_count += 1
                    logger.debug(f"Removed old session file: {filename}")
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old session files")
    
    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话统计信息
        
        Args:
            session_id: 会话 ID
        
        Returns:
            统计信息字典
        """
        messages = await self.get_conversation_history(session_id)
        
        user_messages = [m for m in messages if m.role == MessageRole.USER]
        assistant_messages = [m for m in messages if m.role == MessageRole.ASSISTANT]
        
        return {
            "session_id": session_id,
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "total_tokens": sum(len(m.content) for m in messages),  # 粗略估计
        }

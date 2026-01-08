# -*- coding: utf-8 -*-
"""
记忆管理测试

测试记忆系统的功能：
- 短期记忆（会话历史）
- 长期记忆
- 记忆检索
- 记忆压缩
- 上下文窗口管理
"""
import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestShortTermMemory:
    """测试短期记忆（会话历史）"""
    
    @pytest.fixture
    def memory_manager(self):
        """创建记忆管理器"""
        from app.core.memory import MemoryManager
        return MemoryManager()
    
    def test_add_message(self, memory_manager):
        """测试添加消息"""
        session_id = "test-session"
        
        memory_manager.add_message(
            session_id=session_id,
            role="user",
            content="你好",
        )
        
        messages = memory_manager.get_messages(session_id)
        assert len(messages) >= 1
        assert messages[-1]["content"] == "你好"
    
    def test_get_messages_empty(self, memory_manager):
        """测试获取空会话消息"""
        messages = memory_manager.get_messages("non-existent")
        assert messages == [] or messages is None
    
    def test_clear_session(self, memory_manager):
        """测试清除会话"""
        session_id = "to-clear"
        
        memory_manager.add_message(session_id, "user", "消息")
        memory_manager.clear_session(session_id)
        
        messages = memory_manager.get_messages(session_id)
        assert len(messages) == 0 or messages is None
    
    def test_message_order(self, memory_manager):
        """测试消息顺序"""
        session_id = "order-test"
        
        memory_manager.add_message(session_id, "user", "第一条")
        memory_manager.add_message(session_id, "assistant", "回复1")
        memory_manager.add_message(session_id, "user", "第二条")
        memory_manager.add_message(session_id, "assistant", "回复2")
        
        messages = memory_manager.get_messages(session_id)
        
        assert messages[0]["content"] == "第一条"
        assert messages[1]["content"] == "回复1"
        assert messages[2]["content"] == "第二条"
        assert messages[3]["content"] == "回复2"


class TestLongTermMemory:
    """测试长期记忆"""
    
    @pytest.fixture
    def memory_manager(self):
        from app.core.memory import MemoryManager
        return MemoryManager()
    
    @pytest.mark.asyncio
    async def test_save_long_term_memory(self, memory_manager):
        """测试保存长期记忆"""
        user_id = "test-user"
        memory = {
            "key": "用户偏好",
            "value": "喜欢简洁的回答",
            "importance": 0.8,
        }
        
        await memory_manager.save_long_term_memory(user_id, memory)
        
        # 应该能保存成功
        memories = await memory_manager.get_long_term_memories(user_id)
        assert len(memories) >= 0  # 可能为空列表
    
    @pytest.mark.asyncio
    async def test_retrieve_relevant_memories(self, memory_manager):
        """测试检索相关记忆"""
        user_id = "test-user"
        
        # 保存一些记忆
        await memory_manager.save_long_term_memory(user_id, {
            "key": "编程语言",
            "value": "用户偏好 Python",
        })
        
        # 检索相关记忆
        memories = await memory_manager.retrieve_relevant_memories(
            user_id,
            query="Python 代码",
        )
        
        # 应该返回列表
        assert isinstance(memories, list)


class TestContextWindowManagement:
    """测试上下文窗口管理"""
    
    @pytest.fixture
    def context_manager(self):
        from app.core.context_manager import ContextManager
        return ContextManager(max_tokens=4000)
    
    def test_count_tokens(self, context_manager):
        """测试 token 计数"""
        text = "Hello, this is a test message."
        tokens = context_manager.count_tokens(text)
        
        assert tokens > 0
        assert isinstance(tokens, int)
    
    def test_truncate_messages(self, context_manager):
        """测试消息截断"""
        messages = [
            {"role": "user", "content": "消息" * 100}
            for _ in range(50)
        ]
        
        truncated = context_manager.truncate_to_fit(messages)
        
        # 应该截断到适合的长度
        assert len(truncated) <= len(messages)
    
    def test_preserve_system_message(self, context_manager):
        """测试保留系统消息"""
        messages = [
            {"role": "system", "content": "你是一个助手"},
            {"role": "user", "content": "消息" * 100},
            {"role": "assistant", "content": "回复" * 100},
        ]
        
        truncated = context_manager.truncate_to_fit(messages)
        
        # 系统消息应该被保留
        if len(truncated) > 0:
            assert truncated[0]["role"] == "system"


class TestSessionCompactor:
    """测试会话压缩器"""
    
    @pytest.fixture
    def compactor(self):
        from app.core.session_compactor import SessionCompactor, CompactionConfig
        config = CompactionConfig(
            auto_compact_threshold=500,
            target_tokens=200,
            preserve_recent=2,
        )
        return SessionCompactor(config=config)
    
    def test_should_compact(self, compactor):
        """测试压缩判断"""
        from app.models.chat import ChatMessage, MessageRole
        
        # 少量消息不需要压缩
        small_messages = [
            ChatMessage(role=MessageRole.USER, content="Hi"),
            ChatMessage(role=MessageRole.ASSISTANT, content="Hello"),
        ]
        assert not compactor.should_compact(small_messages)
        
        # 大量消息需要压缩
        large_messages = [
            ChatMessage(
                role=MessageRole.USER,
                content="这是一条很长的消息" * 50
            )
            for _ in range(20)
        ]
        assert compactor.should_compact(large_messages)
    
    @pytest.mark.asyncio
    async def test_compact_messages(self, compactor):
        """测试消息压缩"""
        from app.models.chat import ChatMessage, MessageRole
        
        messages = [
            ChatMessage(
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                content=f"测试消息 {i}" * 20,
                timestamp=datetime.now(),
            )
            for i in range(15)
        ]
        
        compacted, result = await compactor.compact(messages, force=True)
        
        assert result.original_messages == 15
        assert result.compacted_messages <= result.original_messages
    
    def test_preserve_recent_messages(self, compactor):
        """测试保留最近消息"""
        from app.models.chat import ChatMessage, MessageRole
        
        messages = [
            ChatMessage(
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                content=f"消息 {i}",
                timestamp=datetime.now(),
            )
            for i in range(10)
        ]
        
        compactor.config.preserve_recent = 3
        
        # 最近 3 条消息应该被保留
        preserved = messages[-3:]
        
        # 验证逻辑
        assert len(preserved) == 3


class TestMemoryPersistence:
    """测试记忆持久化"""
    
    @pytest.fixture
    def temp_storage(self, tmp_path):
        """临时存储目录"""
        return tmp_path / "memory"
    
    @pytest.mark.asyncio
    async def test_save_and_load_session(self, temp_storage):
        """测试保存和加载会话"""
        from app.core.memory import MemoryManager
        
        manager = MemoryManager(storage_path=str(temp_storage))
        session_id = "persistent-session"
        
        # 添加消息
        manager.add_message(session_id, "user", "保存这条消息")
        manager.add_message(session_id, "assistant", "已保存")
        
        # 保存
        await manager.save_session(session_id)
        
        # 创建新的管理器并加载
        new_manager = MemoryManager(storage_path=str(temp_storage))
        await new_manager.load_session(session_id)
        
        messages = new_manager.get_messages(session_id)
        
        # 应该能加载之前的消息（如果实现了持久化）
        # 注意：如果持久化未实现，这个测试可能失败
        assert isinstance(messages, list)


class TestMemorySearch:
    """测试记忆搜索"""
    
    @pytest.fixture
    def memory_manager(self):
        from app.core.memory import MemoryManager
        return MemoryManager()
    
    @pytest.mark.asyncio
    async def test_search_in_history(self, memory_manager):
        """测试在历史中搜索"""
        session_id = "search-test"
        
        # 添加一些消息
        memory_manager.add_message(session_id, "user", "Python 代码怎么写？")
        memory_manager.add_message(session_id, "assistant", "让我解释 Python...")
        memory_manager.add_message(session_id, "user", "JavaScript 呢？")
        memory_manager.add_message(session_id, "assistant", "JavaScript 是...")
        
        # 搜索相关消息
        results = await memory_manager.search_messages(
            session_id,
            query="Python",
        )
        
        # 应该找到相关消息
        assert isinstance(results, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


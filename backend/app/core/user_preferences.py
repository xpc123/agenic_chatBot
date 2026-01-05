# -*- coding: utf-8 -*-
"""
用户偏好学习系统 - User Preferences

模仿 Cursor 的个性化能力：
1. 响应风格偏好：简洁/详细/技术性
2. 语言偏好：中文/英文/混合
3. 常用工具偏好：记录用户常用的工具
4. 专业领域：推断用户的专业领域
5. 交互习惯：学习用户的交互模式

通过学习让 AI 越来越懂用户！
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
import json
import os


class ResponseStyle(Enum):
    """响应风格"""
    CONCISE = "concise"      # 简洁
    DETAILED = "detailed"    # 详细
    TECHNICAL = "technical"  # 技术性
    CASUAL = "casual"        # 随意


class Language(Enum):
    """语言偏好"""
    CHINESE = "chinese"
    ENGLISH = "english"
    MIXED = "mixed"


@dataclass
class ToolUsageStats:
    """工具使用统计"""
    tool_name: str
    use_count: int = 0
    success_count: int = 0
    last_used: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        return self.success_count / self.use_count if self.use_count > 0 else 0


@dataclass
class TopicInterest:
    """话题兴趣"""
    topic: str
    mention_count: int = 0
    last_mentioned: Optional[datetime] = None


@dataclass
class UserProfile:
    """
    用户画像
    
    包含用户的所有偏好和统计信息
    """
    user_id: str
    
    # 基本偏好
    response_style: ResponseStyle = ResponseStyle.DETAILED
    language: Language = Language.CHINESE
    
    # 工具使用
    tool_usage: Dict[str, ToolUsageStats] = field(default_factory=dict)
    favorite_tools: List[str] = field(default_factory=list)
    
    # 专业领域
    domains: List[str] = field(default_factory=list)
    topics: Dict[str, TopicInterest] = field(default_factory=dict)
    
    # 交互统计
    total_messages: int = 0
    avg_message_length: float = 0
    prefers_code_blocks: bool = True
    prefers_emojis: bool = True
    
    # 时间信息
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "response_style": self.response_style.value,
            "language": self.language.value,
            "tool_usage": {
                name: {
                    "use_count": stats.use_count,
                    "success_count": stats.success_count,
                    "last_used": stats.last_used.isoformat() if stats.last_used else None,
                }
                for name, stats in self.tool_usage.items()
            },
            "favorite_tools": self.favorite_tools,
            "domains": self.domains,
            "topics": {
                name: {
                    "mention_count": topic.mention_count,
                    "last_mentioned": topic.last_mentioned.isoformat() if topic.last_mentioned else None,
                }
                for name, topic in self.topics.items()
            },
            "total_messages": self.total_messages,
            "avg_message_length": self.avg_message_length,
            "prefers_code_blocks": self.prefers_code_blocks,
            "prefers_emojis": self.prefers_emojis,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        profile = cls(user_id=data["user_id"])
        
        profile.response_style = ResponseStyle(data.get("response_style", "detailed"))
        profile.language = Language(data.get("language", "chinese"))
        profile.favorite_tools = data.get("favorite_tools", [])
        profile.domains = data.get("domains", [])
        profile.total_messages = data.get("total_messages", 0)
        profile.avg_message_length = data.get("avg_message_length", 0)
        profile.prefers_code_blocks = data.get("prefers_code_blocks", True)
        profile.prefers_emojis = data.get("prefers_emojis", True)
        
        # 解析工具使用
        for name, stats in data.get("tool_usage", {}).items():
            profile.tool_usage[name] = ToolUsageStats(
                tool_name=name,
                use_count=stats.get("use_count", 0),
                success_count=stats.get("success_count", 0),
                last_used=datetime.fromisoformat(stats["last_used"]) if stats.get("last_used") else None,
            )
        
        # 解析话题
        for name, topic in data.get("topics", {}).items():
            profile.topics[name] = TopicInterest(
                topic=name,
                mention_count=topic.get("mention_count", 0),
                last_mentioned=datetime.fromisoformat(topic["last_mentioned"]) if topic.get("last_mentioned") else None,
            )
        
        if "created_at" in data:
            profile.created_at = datetime.fromisoformat(data["created_at"])
        if "last_active" in data:
            profile.last_active = datetime.fromisoformat(data["last_active"])
        
        return profile


class UserPreferenceManager:
    """
    用户偏好管理器
    
    核心能力：
    1. 从交互中学习偏好
    2. 持久化存储
    3. 应用偏好到响应
    """
    
    # 领域关键词
    DOMAIN_KEYWORDS = {
        "web开发": ["html", "css", "javascript", "react", "vue", "前端", "后端", "api"],
        "数据科学": ["pandas", "numpy", "机器学习", "深度学习", "数据分析", "模型"],
        "系统运维": ["linux", "docker", "kubernetes", "部署", "服务器", "shell"],
        "嵌入式": ["芯片", "电路", "verilog", "skill", "virtuoso", "eda"],
        "移动开发": ["android", "ios", "flutter", "react native", "app"],
        "数据库": ["sql", "mysql", "postgresql", "mongodb", "redis"],
    }
    
    def __init__(self, storage_dir: str = "./data/user_preferences"):
        """
        初始化用户偏好管理器
        
        Args:
            storage_dir: 存储目录
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 内存缓存
        self.profiles: Dict[str, UserProfile] = {}
        
        logger.info(f"UserPreferenceManager initialized at {storage_dir}")
    
    def get_or_create(self, user_id: str) -> UserProfile:
        """获取或创建用户画像"""
        if user_id in self.profiles:
            return self.profiles[user_id]
        
        # 尝试从文件加载
        profile = self._load_profile(user_id)
        if profile is None:
            profile = UserProfile(user_id=user_id)
        
        self.profiles[user_id] = profile
        return profile
    
    def learn_from_message(
        self,
        user_id: str,
        message: str,
        response: Optional[str] = None,
        feedback: Optional[str] = None,  # "positive", "negative", None
    ) -> None:
        """
        从消息中学习用户偏好
        
        Args:
            user_id: 用户 ID
            message: 用户消息
            response: AI 响应（可选）
            feedback: 用户反馈（可选）
        """
        profile = self.get_or_create(user_id)
        
        # 更新基本统计
        profile.total_messages += 1
        profile.last_active = datetime.now()
        
        # 更新平均消息长度
        old_avg = profile.avg_message_length
        profile.avg_message_length = (
            (old_avg * (profile.total_messages - 1) + len(message)) / profile.total_messages
        )
        
        # 检测语言偏好
        self._detect_language(profile, message)
        
        # 检测领域
        self._detect_domains(profile, message)
        
        # 检测话题
        self._detect_topics(profile, message)
        
        # 根据反馈调整
        if feedback == "positive" and response:
            self._learn_positive(profile, response)
        elif feedback == "negative" and response:
            self._learn_negative(profile, response)
        
        # 保存
        self._save_profile(profile)
    
    def learn_from_tool_usage(
        self,
        user_id: str,
        tool_name: str,
        success: bool,
    ) -> None:
        """
        从工具使用中学习
        
        Args:
            user_id: 用户 ID
            tool_name: 工具名
            success: 是否成功
        """
        profile = self.get_or_create(user_id)
        
        if tool_name not in profile.tool_usage:
            profile.tool_usage[tool_name] = ToolUsageStats(tool_name=tool_name)
        
        stats = profile.tool_usage[tool_name]
        stats.use_count += 1
        if success:
            stats.success_count += 1
        stats.last_used = datetime.now()
        
        # 更新常用工具列表
        self._update_favorite_tools(profile)
        
        # 保存
        self._save_profile(profile)
    
    def _detect_language(self, profile: UserProfile, message: str) -> None:
        """检测语言偏好"""
        # 简单检测：中文字符占比
        chinese_chars = sum(1 for c in message if '\u4e00' <= c <= '\u9fff')
        ratio = chinese_chars / len(message) if message else 0
        
        if ratio > 0.5:
            profile.language = Language.CHINESE
        elif ratio < 0.1:
            profile.language = Language.ENGLISH
        else:
            profile.language = Language.MIXED
    
    def _detect_domains(self, profile: UserProfile, message: str) -> None:
        """检测专业领域"""
        message_lower = message.lower()
        
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in message_lower)
            if matches >= 2 and domain not in profile.domains:
                profile.domains.append(domain)
                logger.debug(f"Detected domain: {domain}")
    
    def _detect_topics(self, profile: UserProfile, message: str) -> None:
        """检测话题兴趣"""
        # 提取关键词（简单实现）
        import re
        words = re.findall(r'\b\w{3,}\b', message.lower())
        
        # 技术关键词
        tech_keywords = [
            "python", "javascript", "api", "docker", "linux", "git",
            "数据库", "算法", "性能", "优化", "测试", "部署",
        ]
        
        for word in words:
            if word in tech_keywords:
                if word not in profile.topics:
                    profile.topics[word] = TopicInterest(topic=word)
                profile.topics[word].mention_count += 1
                profile.topics[word].last_mentioned = datetime.now()
    
    def _learn_positive(self, profile: UserProfile, response: str) -> None:
        """从正面反馈中学习"""
        # 检测响应风格
        if len(response) < 200:
            profile.response_style = ResponseStyle.CONCISE
        elif len(response) > 1000:
            profile.response_style = ResponseStyle.DETAILED
        
        # 检测代码块偏好
        if "```" in response:
            profile.prefers_code_blocks = True
        
        # 检测 emoji 偏好
        import re
        emojis = re.findall(r'[\U0001F300-\U0001F9FF]', response)
        if emojis:
            profile.prefers_emojis = True
    
    def _learn_negative(self, profile: UserProfile, response: str) -> None:
        """从负面反馈中学习"""
        # 可能需要调整风格
        if profile.response_style == ResponseStyle.DETAILED:
            # 尝试更简洁
            profile.response_style = ResponseStyle.CONCISE
        elif profile.response_style == ResponseStyle.CONCISE:
            # 尝试更详细
            profile.response_style = ResponseStyle.DETAILED
    
    def _update_favorite_tools(self, profile: UserProfile) -> None:
        """更新常用工具列表"""
        # 按使用次数排序
        sorted_tools = sorted(
            profile.tool_usage.items(),
            key=lambda x: x[1].use_count,
            reverse=True,
        )
        
        # 取前5个
        profile.favorite_tools = [name for name, _ in sorted_tools[:5]]
    
    def get_style_prompt(self, user_id: str) -> str:
        """
        获取风格提示词
        
        用于注入到系统提示中，引导 AI 按用户偏好回复
        """
        profile = self.get_or_create(user_id)
        
        prompts = []
        
        # 响应风格
        style_prompts = {
            ResponseStyle.CONCISE: "请简洁回答，突出重点，避免冗长",
            ResponseStyle.DETAILED: "请详细解释，包含背景知识和示例",
            ResponseStyle.TECHNICAL: "请使用专业术语，假设用户有技术背景",
            ResponseStyle.CASUAL: "请用轻松友好的语气回答",
        }
        prompts.append(style_prompts.get(profile.response_style, ""))
        
        # 语言
        if profile.language == Language.CHINESE:
            prompts.append("请用中文回答")
        elif profile.language == Language.ENGLISH:
            prompts.append("Please respond in English")
        
        # 领域
        if profile.domains:
            prompts.append(f"用户熟悉领域: {', '.join(profile.domains)}")
        
        # 代码块
        if profile.prefers_code_blocks:
            prompts.append("在需要时使用代码块格式化代码")
        
        return "\n".join(filter(None, prompts))
    
    def get_suggested_tools(self, user_id: str) -> List[str]:
        """获取推荐工具（基于历史使用）"""
        profile = self.get_or_create(user_id)
        return profile.favorite_tools[:3]
    
    def _load_profile(self, user_id: str) -> Optional[UserProfile]:
        """从文件加载用户画像"""
        file_path = self.storage_dir / f"{user_id}.json"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return UserProfile.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load profile for {user_id}: {e}")
            return None
    
    def _save_profile(self, profile: UserProfile) -> None:
        """保存用户画像到文件"""
        file_path = self.storage_dir / f"{profile.user_id}.json"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save profile for {profile.user_id}: {e}")
    
    def get_user_summary(self, user_id: str) -> Dict[str, Any]:
        """获取用户摘要"""
        profile = self.get_or_create(user_id)
        
        return {
            "user_id": user_id,
            "response_style": profile.response_style.value,
            "language": profile.language.value,
            "domains": profile.domains,
            "favorite_tools": profile.favorite_tools,
            "total_messages": profile.total_messages,
            "active_days": (datetime.now() - profile.created_at).days,
            "top_topics": sorted(
                profile.topics.items(),
                key=lambda x: x[1].mention_count,
                reverse=True,
            )[:5],
        }


# 全局实例
_preference_manager: Optional[UserPreferenceManager] = None


def get_preference_manager(storage_dir: str = "./data/user_preferences") -> UserPreferenceManager:
    """获取用户偏好管理器实例"""
    global _preference_manager
    if _preference_manager is None:
        _preference_manager = UserPreferenceManager(storage_dir)
    return _preference_manager


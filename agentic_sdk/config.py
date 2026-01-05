# -*- coding: utf-8 -*-
"""
SDK 配置
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LLMConfig:
    """
    LLM 配置
    """
    provider: str = "jedai"  # jedai, openai, anthropic, ollama
    model: str = "GCP_claude-sonnet-4-5"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60


@dataclass
class RAGConfig:
    """
    RAG 配置
    """
    enabled: bool = True
    vector_store: str = "faiss"  # faiss, chroma
    embedding_model: str = "JEDAI_MODEL_INT_EMBED_2"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 5
    score_threshold: float = 0.5


@dataclass
class MemoryConfig:
    """
    记忆配置
    """
    enabled: bool = True
    type: str = "buffer_window"  # buffer, buffer_window, summary
    max_messages: int = 20
    enable_long_term: bool = True


@dataclass
class SkillsConfig:
    """
    Skills 配置
    """
    enabled: bool = True
    auto_detect: bool = True  # 自动检测触发词
    builtin_skills: bool = True  # 加载内置技能


@dataclass
class MCPConfig:
    """
    MCP 配置
    """
    enabled: bool = True
    servers: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ChatConfig:
    """
    ChatBot 完整配置
    
    使用方式::
    
        config = ChatConfig(
            enable_rag=True,
            enable_memory=True,
            llm=LLMConfig(model="gpt-4"),
        )
        bot = ChatBot(config)
    """
    # 功能开关
    enable_rag: bool = True
    enable_memory: bool = True
    enable_skills: bool = True
    enable_mcp: bool = True
    enable_preferences: bool = True
    
    # 详细配置
    llm: LLMConfig = field(default_factory=LLMConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    skills: SkillsConfig = field(default_factory=SkillsConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    
    # 数据目录
    data_dir: Path = field(default_factory=lambda: Path("./data"))
    
    # 系统提示词
    system_prompt: str = """你是一个智能助手，可以帮助用户完成各种任务。
你具备以下能力：
- 回答问题和进行对话
- 使用工具执行操作
- 搜索知识库获取信息
- 记住对话历史和用户偏好

请用友好、专业的方式与用户交流。"""
    
    # 日志
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    def __post_init__(self):
        """确保数据目录存在"""
        self.data_dir = Path(self.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def minimal(cls) -> "ChatConfig":
        """最小配置（仅对话）"""
        return cls(
            enable_rag=False,
            enable_memory=False,
            enable_skills=False,
            enable_mcp=False,
            enable_preferences=False,
        )
    
    @classmethod
    def full(cls) -> "ChatConfig":
        """完整配置（所有功能）"""
        return cls(
            enable_rag=True,
            enable_memory=True,
            enable_skills=True,
            enable_mcp=True,
            enable_preferences=True,
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatConfig":
        """从字典创建配置"""
        return cls(**data)
    
    @classmethod
    def from_file(cls, path: str) -> "ChatConfig":
        """从文件加载配置"""
        import json
        import yaml
        
        path = Path(path)
        
        if path.suffix == ".json":
            with open(path) as f:
                data = json.load(f)
        elif path.suffix in [".yaml", ".yml"]:
            with open(path) as f:
                data = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported config file format: {path.suffix}")
        
        return cls.from_dict(data)


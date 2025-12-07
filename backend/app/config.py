"""
应用配置管理
"""
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from pathlib import Path
import os


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    APP_NAME: str = "Agentic ChatBot"
    APP_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = Field(default=8000, ge=1, le=65535, description="服务端口号")
    DEBUG: bool = True
    
    # LLM配置
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API密钥")
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_MAX_TOKENS: int = 4096
    
    # Anthropic配置 (可选)
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-opus-20240229"
    
    # Embedding配置
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    
    # 向量数据库配置
    VECTOR_DB_TYPE: str = "chroma"  # chroma, faiss, pinecone
    CHROMA_PERSIST_DIR: str = "./data/vector_db/chroma"
    FAISS_INDEX_PATH: str = "./data/vector_db/faiss"
    
    # RAG配置
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K_RETRIEVAL: int = 5
    SIMILARITY_THRESHOLD: float = 0.7
    
    # 文档存储
    UPLOAD_DIR: str = "./data/documents"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt", ".md", ".html"]
    
    # 记忆配置
    MEMORY_TYPE: str = "buffer_window"  # buffer, buffer_window, summary
    MEMORY_WINDOW_SIZE: int = 10
    LONG_TERM_MEMORY_DIR: str = "./data/memory"
    
    # MCP配置
    MCP_SERVERS_CONFIG: str = "./config/mcp_servers.json"
    MCP_TIMEOUT: int = 30
    MCP_MAX_RETRIES: int = 3
    
    # Agent配置
    MAX_ITERATIONS: int = 10
    AGENT_TYPE: str = "react"  # react, plan_execute, openai_functions
    ENABLE_PLANNING: bool = True
    ENABLE_REFLECTION: bool = True
    
    # @路径引用配置
    ENABLE_PATH_REFERENCE: bool = True
    MAX_FILE_SIZE_FOR_CONTEXT: int = 1024 * 1024  # 1MB
    ALLOWED_PATH_PATTERNS: List[str] = ["**/*.py", "**/*.md", "**/*.txt", "**/*.json", "**/*.yaml"]
    WORKSPACE_ROOT: Optional[str] = None  # 工作区根路径，None时使用当前目录
    
    # 对话配置
    MAX_CONVERSATION_HISTORY: int = 50
    SESSION_TIMEOUT: int = 3600  # 1小时
    
    # SDK集成配置
    SDK_API_KEY: Optional[str] = None  # B端集成时的API密钥
    ENABLE_WEBHOOK: bool = False  # 是否启用webhook回调
    WEBHOOK_URL: Optional[str] = None
    WEBHOOK_SECRET: Optional[str] = None
    
    # Redis配置 (可选，用于分布式部署)
    REDIS_URL: Optional[str] = None
    REDIS_TTL: int = 86400  # 24小时
    
    # CORS配置
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"
    
    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}, got {v}")
        return v_upper
    
    @field_validator('VECTOR_DB_TYPE')
    @classmethod
    def validate_vector_db_type(cls, v: str) -> str:
        """验证向量数据库类型"""
        valid_types = ['chroma', 'faiss', 'pinecone']
        if v.lower() not in valid_types:
            raise ValueError(f"VECTOR_DB_TYPE must be one of {valid_types}, got {v}")
        return v.lower()
    
    @field_validator('MEMORY_TYPE')
    @classmethod
    def validate_memory_type(cls, v: str) -> str:
        """验证记忆类型"""
        valid_types = ['buffer', 'buffer_window', 'summary']
        if v.lower() not in valid_types:
            raise ValueError(f"MEMORY_TYPE must be one of {valid_types}, got {v}")
        return v.lower()
    
    @field_validator('AGENT_TYPE')
    @classmethod
    def validate_agent_type(cls, v: str) -> str:
        """验证Agent类型"""
        valid_types = ['react', 'plan_execute', 'openai_functions']
        if v.lower() not in valid_types:
            raise ValueError(f"AGENT_TYPE must be one of {valid_types}, got {v}")
        return v.lower()
    
    def validate_required_settings(self):
        """验证必需的配置项"""
        errors = []
        
        # 验证 OPENAI_API_KEY
        if not self.OPENAI_API_KEY or self.OPENAI_API_KEY.strip() == "":
            errors.append("OPENAI_API_KEY is required")
        
        # 验证日志目录
        log_path = Path(self.LOG_FILE)
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            # 检查写入权限
            test_file = log_path.parent / ".write_test"
            try:
                test_file.touch()
                test_file.unlink()
            except Exception:
                errors.append(f"Log directory is not writable: {log_path.parent}")
        except Exception as e:
            errors.append(f"Cannot create log directory: {e}")
        
        # 验证数据目录
        for dir_path in [
            self.CHROMA_PERSIST_DIR,
            self.FAISS_INDEX_PATH,
            self.UPLOAD_DIR,
            self.LONG_TERM_MEMORY_DIR,
        ]:
            try:
                Path(dir_path).parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create data directory {dir_path}: {e}")
        
        if errors:
            from .exceptions import ConfigurationError
            raise ConfigurationError(
                message="Configuration validation failed",
                details={"errors": errors}
            )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 全局配置实例
settings = Settings()

# 启动时验证配置
try:
    settings.validate_required_settings()
except Exception as e:
    import sys
    print(f"❌ Configuration error: {e}", file=sys.stderr)
    sys.exit(1)

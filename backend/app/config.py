# -*- coding: utf-8 -*-
"""
应用配置管理
"""
from typing import Optional, List, Literal
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from pathlib import Path
import os


# JedAI 支持的 LLM 模型列表
JEDAI_SUPPORTED_LLM_MODELS = {
    # On-prem 模型
    "on_prem": [
        "Llama3.1_JEDAI_MODEL_CHAT_2",
        "Llama3.3_JEDAI_MODEL_CHAT_2",
        "nvidia/llama-3_3-nemotron-super-49b-v1_5",
        "Qwen3-32B",
        "openai/gpt-oss-120b",
    ],
    # GCP 模型 (通过 JedAI 代理)
    "gcp_gemini": [
        "gemini-2.5-pro",
        "gemini-2.5-flash", 
        "gemini-2.5-flash-lite",
        "gemini-3-pro-preview",
    ],
    "gcp_claude": [
        "claude-sonnet-4-5",
        "claude-haiku-4-5",
        "claude-sonnet-4",
        "claude-3-7-sonnet",
        "claude-opus-4-1",
        "claude-3-5-haiku",
        "claude-3-5-sonnet-v2",
    ],
    "gcp_llama": [
        "meta/llama-3.1-70b-instruct-maas",
        "meta/llama-3.3-70b-instruct-maas",
        "meta/llama-3.1-405b-instruct-maas",
        "meta/llama-3.1-8b-instruct-maas",
        "meta/llama-4-scout-17b-16e-instruct-maas",
        "meta/llama-4-maverick-17b-128e-instruct-maas",
    ],
    "gcp_qwen": [
        "qwen/qwen3-235b-a22b-instruct-2507-maas",
        "qwen/qwen3-coder-480b-a35b-instruct-maas",
    ],
    "gcp_deepseek": [
        "deepseek-ai/deepseek-v3.1-maas",
        "deepseek-ai/deepseek-r1-0528-maas",
    ],
    "gcp_openai": [
        "openai/gpt-oss-120b-maas",
    ],
    # Azure OpenAI 模型 (注意: 成本较高，不推荐使用)
    "azure": [
        "gpt-4o",
        "o4-mini",
        "gpt-5",
        "gpt-5-mini",
        "gpt-5-2",
        "rnd01-gpt4-vision",
    ],
    # AWS Bedrock 模型
    "aws": [
        "amazon.titan-text-express-v1",
        "amazon.titan-text-lite-v1",
        "anthropic.claude-3-haiku-20240307-v1:0",
        "anthropic.claude-3-opus-20240229-v1:0",
        "anthropic.claude-3-5-haiku-20241022-v1:0",
        "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "us.anthropic.claude-sonnet-4-20250514-v1:0",
        "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        "us.anthropic.claude-opus-4-20250514-v1:0",
        "us.anthropic.claude-opus-4-1-20250805-v1:0",
    ],
}

# JedAI 支持的 Embedding 模型
JEDAI_SUPPORTED_EMBEDDING_MODELS = {
    "http": [
        "JEDAI_MODEL_INT_EMBED_2",
        "bge-large-en-v1.5",
        "Qwen3-Embedding-4B",
        "embeddinggemma-300m",
    ],
    "aws": [
        "amazon.titan-embed-text-v1",
        "amazon.titan-embed-text-v2:0",
        "cohere.embed-english-v3",
        "cohere.embed-multilingual-v3",
    ],
    "gcp": [
        "text-multilingual-embedding-002",
        "text-embedding-004",
        "text-embedding-005",
        "gemini-embedding-001",
    ],
    "azure": [
        "text-embedding-3-small",
        "text-embedding-ada-002",
    ],
}

# JedAI 支持的 Rerank 模型
JEDAI_SUPPORTED_RERANK_MODELS = {
    "http": [
        "JEDAI_MODEL_RERANK_2",
        "bge-reranker-v2-m3",
        "Qwen3-Reranker-4B",
    ],
    "aws": [
        "amazon.rerank-v1:0",
        "cohere.rerank-v3-5:0",
    ],
    "gcp": [
        "semantic-ranker-default@latest",
        "semantic-ranker-default-004",
        "semantic-ranker-fast-004",
        "semantic-ranker-default-003",
        "semantic-ranker-default-002",
    ],
}

# JedAI LangChain 集成模型名称映射
# 用于 langchain_openai.ChatOpenAI 的 model_name 参数
JEDAI_LANGCHAIN_MODEL_NAMES = {
    "on_prem": "Llama3.1_JEDAI_MODEL_CHAT_2",  # 或 Llama3.3_JEDAI_MODEL_CHAT_2
    "azure": "AzureOpenAI",
    "claude": "Claude",
    "gemini": "GEMINI",
    "gcp_oss": "gcp_oss",
}


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    APP_NAME: str = "Agentic ChatBot"
    APP_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = Field(default=8000, ge=1, le=65535, description="服务端口号")
    DEBUG: bool = True
    
    # LLM配置
    LLM_PROVIDER: str = "jedai"  # openai, jedai, anthropic, ollama
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API密钥")
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_MAX_TOKENS: int = 4096
    
    # Anthropic配置 (可选)
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-opus-20240229"
    
    # JedAI配置 (Cadence Internal)
    JEDAI_API_KEY: Optional[str] = None  # Bearer token from login
    JEDAI_API_BASE: str = "http://sjf-dsgdspr-084.cadence.com:5668"
    JEDAI_LLM_ENDPOINT: str = "/api/copilot/v1/llm/chat/completions"
    JEDAI_EMBEDDING_ENDPOINT: str = "/api/copilot/v1/llm/embeddings"
    JEDAI_RERANK_ENDPOINT: str = "/api/copilot/v1/llm/rerank"
    JEDAI_LOGIN_ENDPOINT: str = "/api/v1/security/login"
    
    # JedAI LLM 模型配置
    # 模型类型: on_prem, AzureOpenAI, Claude, GEMINI, gcp_oss, AWSBedrock
    JEDAI_MODEL_TYPE: str = "gcp_oss"  # JedAI model type for API routing
    JEDAI_MODEL: str = "meta/llama-3.3-70b-instruct-maas"  # 默认使用 Llama 3.3
    JEDAI_TIMEOUT: int = 120
    JEDAI_VERIFY_SSL: bool = False
    JEDAI_MAX_TOKENS: int = 8000
    JEDAI_TEMPERATURE: float = 0.7
    JEDAI_TOP_P: float = 1.0
    
    # JedAI GCP 配置 (用于 Gemini, Claude, Llama 等 GCP 模型)
    JEDAI_GCP_PROJECT: str = "gcp-cdns-llm-test"
    JEDAI_GCP_LOCATION: str = "us-central1"  # 不同模型可能需要不同 location
    
    # JedAI Azure 配置 (用于 Azure OpenAI 模型)
    JEDAI_AZURE_ENDPOINT: str = "https://llmtest01-eastus2.openai.azure.com"
    JEDAI_AZURE_API_VERSION: str = "2025-01-01-preview"
    JEDAI_AZURE_DEPLOYMENT: str = "gpt-4o"
    
    # JedAI AWS 配置 (用于 AWS Bedrock 模型)
    JEDAI_AWS_SERVICE_NAME: str = "bedrock-runtime"
    JEDAI_AWS_REGION: str = "us-west-2"

    # JedAI Embedding 配置
    JEDAI_EMBEDDING_PROVIDER: str = "gcp"  # http, aws, gcp, azure
    JEDAI_EMBEDDING_MODEL: str = "text-embedding-005"
    JEDAI_EMBEDDING_URL: Optional[str] = None  # 如果需要自定义 embedding URL
    
    # JedAI Rerank 配置
    JEDAI_RERANK_PROVIDER: str = "gcp"  # http, aws, gcp
    JEDAI_RERANK_MODEL: str = "semantic-ranker-default@latest"
    JEDAI_RERANK_URL: Optional[str] = None  # 如果需要自定义 rerank URL
    
    # JedAI 认证配置
    JEDAI_USERNAME: Optional[str] = None  # LDAP username
    JEDAI_PASSWORD: Optional[str] = None  # LDAP password
    JEDAI_AUTH_PROVIDER: str = "LDAP"

    # Embedding配置 (通用)
    EMBEDDING_PROVIDER: str = "jedai"  # openai, jedai, local
    EMBEDDING_MODEL: str = "text-embedding-005"
    EMBEDDING_DIMENSION: int = 768  # GCP text-embedding-005 默认维度
    
    # Rerank 配置 (通用)
    RERANK_ENABLED: bool = True
    RERANK_PROVIDER: str = "jedai"  # jedai, cohere, local
    RERANK_MODEL: str = "semantic-ranker-default@latest"
    RERANK_TOP_N: int = 5
    
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
        
        # 验证 OPENAI_API_KEY (如果未配置 JedAI)
        # if not self.OPENAI_API_KEY or self.OPENAI_API_KEY.strip() == "":
        #     errors.append("OPENAI_API_KEY is required")
        
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
# try:
#     settings.validate_required_settings()
# except Exception as e:
#     import sys
#     print(f"❌ Configuration error: {e}", file=sys.stderr)
#     sys.exit(1)

# -*- coding: utf-8 -*-
"""
LLM 客户端封装 - 基于 LangChain 1.0

LangChain 1.0 核心特性:
- init_chat_model: 统一的模型初始化 API
- init_embeddings: 统一的 Embedding 初始化 API
- 支持模型标识符字符串 (如 "gpt-4o", "claude-sonnet-4-5-20250929")
- 自动推断提供商
"""
from typing import List, Dict, Any, Optional, AsyncGenerator, Union
from langchain_core.language_models import BaseChatModel
from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
import httpx
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableConfig
from loguru import logger

from ..config import settings


# ============================================================================
# JedAI Token 缓存 - 避免重复登录
# ============================================================================
_jedai_token_cache: Dict[str, str] = {}  # {username: token}


def get_cached_jedai_token() -> Optional[str]:
    """获取缓存的 JedAI Token"""
    username = settings.JEDAI_USERNAME
    if username and username in _jedai_token_cache:
        logger.debug(f"Using cached JedAI token for {username}")
        return _jedai_token_cache[username]
    return None


def cache_jedai_token(token: str) -> None:
    """缓存 JedAI Token"""
    username = settings.JEDAI_USERNAME
    if username and token:
        _jedai_token_cache[username] = token
        logger.debug(f"Cached JedAI token for {username}")


class LLMClient:
    """
    LLM 客户端统一接口
    
    基于 LangChain 1.0，使用 init_chat_model 支持:
    - OpenAI (gpt-4o, gpt-4o-mini, gpt-5, etc.)
    - Anthropic (claude-3-5-sonnet, claude-sonnet-4-5, etc.)
    - Google (gemini-1.5-pro, gemini-2.0-flash, etc.)
    - JedAI (Cadence Internal)
    - Ollama (本地模型)
    - 其他兼容的模型提供商
    
    使用示例:
    ```python
    # 使用模型标识符
    client = LLMClient(model="gpt-4o")
    response = await client.chat_completion([
        {"role": "user", "content": "Hello"}
    ])
    
    # 使用完整标识符
    client = LLMClient(model="anthropic:claude-3-5-sonnet")

    # 使用 JedAI
    client = LLMClient(provider="jedai", model="gpt-4")
    ```
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
    ):
        """
        初始化 LLM 客户端
        
        Args:
            provider: 提供商 ("openai", "anthropic", "google", "ollama", "jedai")
            model: 模型名称或完整标识符 (如 "gpt-4o" 或 "openai:gpt-4o")
            temperature: 温度参数 (0.0-2.0)
            api_key: API 密钥
            api_base: API 基础 URL
            max_tokens: 最大 token 数
            timeout: 超时时间（秒）
        """
        self.provider = provider or settings.LLM_PROVIDER
        self.model = model or (settings.JEDAI_MODEL if self.provider == "jedai" else settings.OPENAI_MODEL)
        self.temperature = temperature if temperature is not None else settings.OPENAI_TEMPERATURE
        self.max_tokens = max_tokens or settings.OPENAI_MAX_TOKENS
        self.timeout = timeout or (settings.JEDAI_TIMEOUT if self.provider == "jedai" else 30)
        
        # 使用 LangChain 1.0 的 init_chat_model 初始化
        self.llm = self._init_llm(api_key, api_base)
        
        logger.info(f"LLMClient initialized: {self.provider}/{self.model}")
    
    def _init_llm(self, api_key: Optional[str], api_base: Optional[str]) -> BaseChatModel:
        """
        使用 LangChain 1.0 的 init_chat_model 初始化模型
        
        模型标识符格式:
        - 短格式: "gpt-4o" (自动推断为 "openai:gpt-4o")
        - 长格式: "openai:gpt-4o"
        - Claude: "claude-3-5-sonnet" 或 "anthropic:claude-3-5-sonnet"
        - JedAI: 使用 ChatOpenAI 兼容接口
        """
        # JedAI 特殊处理 (使用 ChatOpenAI 兼容接口)
        if self.provider == "jedai":
            return self._init_jedai(api_key, api_base)

        # 构建模型标识符
        model_id = self._build_model_id()
        
        # 构建初始化参数
        init_kwargs = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
        }
        
        # 根据提供商添加特定参数
        if self.provider == "openai":
            if api_key or settings.OPENAI_API_KEY:
                init_kwargs["api_key"] = api_key or settings.OPENAI_API_KEY
            if api_base or settings.OPENAI_API_BASE:
                base_url = api_base or settings.OPENAI_API_BASE
                if base_url != "https://api.openai.com/v1":
                    init_kwargs["base_url"] = base_url
        
        elif self.provider == "anthropic":
            if api_key or settings.ANTHROPIC_API_KEY:
                init_kwargs["api_key"] = api_key or settings.ANTHROPIC_API_KEY
        
        try:
            return init_chat_model(model_id, **init_kwargs)
        except Exception as e:
            logger.error(f"Failed to initialize model {model_id}: {e}")
            raise

    def _init_jedai(self, api_key: Optional[str], api_base: Optional[str]) -> BaseChatModel:
        """
        初始化 JedAI 客户端 (基于 ChatOpenAI)
        
        JedAI 是 Cadence 内部服务，兼容 OpenAI 接口格式，但需要特殊的认证和路径处理。
        
        JedAI 支持多种模型类型:
        - on_prem: 本地部署模型 (Llama, Qwen, Nemotron 等)
        - gcp_oss: GCP 上的开源模型 (Llama, Qwen, DeepSeek 等)
        - GEMINI: Google Gemini 模型
        - Claude: Anthropic Claude 模型 (通过 GCP)
        - AzureOpenAI: Azure OpenAI 模型
        - AWSBedrock: AWS Bedrock 模型
        
        注意: Azure 成本较高，不推荐使用
        """
        base_url = api_base or settings.JEDAI_API_BASE
        
        # 根据模型类型选择正确的 API 路径
        # - 端口 5668 + /api/copilot/v1/llm: 支持 on_prem, gcp_oss
        # - 端口 2513 + /api/assistant/v1/llm: 支持所有模型，包括 Claude, Gemini
        model_type = settings.JEDAI_MODEL_TYPE.lower()
        
        # 确保 base_url 包含正确的 API 路径
        if not base_url.endswith("/llm"):
            # 根据模型类型选择 API 端点
            if model_type in ["claude", "gcp_claude", "gemini", "gcp_gemini", "azure", "azureopenai", "aws", "awsbedrock"]:
                # 使用 assistant API (支持更多模型)
                base_url = f"{base_url.rstrip('/')}/api/assistant/v1/llm"
            else:
                # 使用 copilot API (on_prem, gcp_oss 等)
                base_url = f"{base_url.rstrip('/')}/api/copilot/v1/llm"
        
        api_key = api_key or settings.JEDAI_API_KEY
        
        # 如果没有 API Key，尝试登录获取
        if not api_key:
            api_key = self._jedai_login()
        
        # 确定 LangChain 集成的模型名称
        # JedAI 使用特定的 model 参数来路由到不同的后端
        langchain_model_name = self._get_jedai_langchain_model_name()
        
        logger.info(f"Initializing JedAI client: {base_url}, model={self.model}, langchain_model={langchain_model_name}")
        
        # JedAI 需要特殊的 headers
        default_headers = {
            "Content-Type": "application/json",
            "accept": "*/*",
        }
        
        # 如果有 API Key，添加到 Authorization header
        if api_key:
            default_headers["Authorization"] = f"Bearer {api_key}"
        
        # 存储 JedAI 特定参数，在请求时使用
        self._jedai_extra_body = self._get_jedai_model_kwargs()
            
        # 使用 ChatOpenAI 作为底层实现，因为 JedAI 兼容 OpenAI 接口
        # 注意：extra_body 参数会被添加到每个请求的 body 中
        return ChatOpenAI(
            model=langchain_model_name,
            openai_api_key=api_key or "dummy-key", # JedAI 可能不需要 key 或者使用 bearer token
            openai_api_base=base_url,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
            default_headers=default_headers,
            http_client=httpx.Client(verify=settings.JEDAI_VERIFY_SSL),
            extra_body=self._jedai_extra_body,  # 使用 extra_body 而不是 model_kwargs
        )
    
    def _jedai_login(self) -> Optional[str]:
        """
        JedAI 登录获取 token（带缓存）
        """
        import httpx as sync_httpx
        
        # 先检查缓存
        cached_token = get_cached_jedai_token()
        if cached_token:
            return cached_token
        
        if not settings.JEDAI_USERNAME or not settings.JEDAI_PASSWORD:
            logger.warning("JedAI username/password not configured, skipping login")
            return None
        
        login_url = f"{settings.JEDAI_API_BASE}/api/v1/security/login"
        
        try:
            with sync_httpx.Client(verify=settings.JEDAI_VERIFY_SSL, timeout=30) as client:
                response = client.post(
                    login_url,
                    headers={"Content-Type": "application/json"},
                    json={
                        "username": settings.JEDAI_USERNAME,
                        "password": settings.JEDAI_PASSWORD,
                        "provider": settings.JEDAI_AUTH_PROVIDER or "LDAP"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    token = data.get('access_token') or data.get('token')
                    if token:
                        logger.info("JedAI login successful")
                        # 缓存 token
                        cache_jedai_token(token)
                        return token
                
                logger.error(f"JedAI login failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"JedAI login error: {e}")
            return None
    
    def _get_jedai_langchain_model_name(self) -> str:
        """
        获取 JedAI 用于 LangChain 的模型名称
        
        JedAI 通过 model 参数来路由请求到不同的后端:
        - on_prem 模型直接使用模型名 (如 Llama3.3_JEDAI_MODEL_CHAT_2)
        - GCP Claude/Gemini 使用完整模型名 (如 GCP_claude-sonnet-4-5)
        - gcp_oss 需要使用 "gcp_oss" 作为 model，deployment 指定具体模型
        - Azure 使用 "AzureOpenAI_xxx"
        - AWS 使用 "AWSBedrock_xxx"
        """
        from ..config import JEDAI_LANGCHAIN_MODEL_NAMES, JEDAI_SUPPORTED_LLM_MODELS
        
        # 检查是否是 on_prem 模型（直接使用模型名）
        if self.model in JEDAI_SUPPORTED_LLM_MODELS.get("on_prem", []):
            return self.model
        
        # 根据 model_type 设置确定 LangChain 模型名
        model_type = settings.JEDAI_MODEL_TYPE.lower()
        
        if model_type == "on_prem":
            return self.model
        elif model_type in ["claude", "gcp_claude"]:
            # Claude 模型直接使用完整模型名 (如 GCP_claude-sonnet-4-5)
            return self.model
        elif model_type in ["gemini", "gcp_gemini"]:
            # Gemini 模型直接使用完整模型名 (如 GCP_gemini-2.5-pro)
            return self.model
        elif model_type in ["azure", "azureopenai"]:
            # Azure 模型直接使用完整模型名 (如 AzureOpenAI_gpt-4o)
            return self.model
        elif model_type in ["aws", "awsbedrock"]:
            # AWS 模型直接使用完整模型名
            return self.model
        elif model_type in ["gcp_oss", "gcp_llama", "gcp_qwen", "gcp_deepseek", "gcp_openai"]:
            # gcp_oss 需要使用 "gcp_oss" 作为 model，具体模型通过 deployment 指定
            return "gcp_oss"
        else:
            # 默认返回配置的模型名或 gcp_oss
            return JEDAI_LANGCHAIN_MODEL_NAMES.get(model_type, self.model)
    
    def _get_jedai_model_kwargs(self) -> Dict[str, Any]:
        """
        获取 JedAI 特定的模型参数 (extra_body)
        
        根据 JedAI 文档:
        - gcp_oss 需要 project, location, deployment 参数
        - Claude/Gemini/Azure/AWS 模型直接使用完整模型名，不需要额外参数
        """
        model_type = settings.JEDAI_MODEL_TYPE.lower()
        kwargs = {}
        
        # 只有 gcp_oss 类型需要额外的 GCP 参数
        if model_type in ["gcp_oss", "gcp_llama", "gcp_qwen", "gcp_deepseek", "gcp_openai"]:
            kwargs["project"] = settings.JEDAI_GCP_PROJECT
            kwargs["location"] = settings.JEDAI_GCP_LOCATION
            kwargs["deployment"] = self.model
        
        # Claude/Gemini/Azure/AWS 直接使用完整模型名，不需要 extra_body
        # 例如: GCP_claude-sonnet-4-5, GCP_gemini-2.5-pro, AzureOpenAI_gpt-4o
        
        return kwargs
    
    def _build_model_id(self) -> str:
        """构建模型标识符"""
        # 如果已经包含提供商前缀，直接返回
        if ":" in self.model:
            return self.model
        
        # 根据提供商添加前缀
        provider_prefixes = {
            "openai": "openai",
            "anthropic": "anthropic",
            "google": "google-genai",
            "ollama": "ollama",
        }
        
        prefix = provider_prefixes.get(self.provider)
        if prefix:
            return f"{prefix}:{self.model}"
        
        # 尝试自动推断
        return self.model
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        聊天补全
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            stream: 是否流式输出
            temperature: 温度参数
            **kwargs: 其他参数
        
        Returns:
            完整响应文本或流式生成器
        """
        # 转换为 LangChain 消息格式
        lc_messages = self._convert_messages(messages)
        
        # 创建运行配置
        config = RunnableConfig(
            configurable={
                "temperature": temperature or self.temperature,
            }
        )
        
        try:
            if stream:
                return self._stream_completion(lc_messages, config)
            else:
                return await self._invoke_completion(lc_messages, config)
        
        except Exception as e:
            logger.error(f"LLM completion error: {e}")
            raise
    
    async def _invoke_completion(
        self,
        messages: List[BaseMessage],
        config: RunnableConfig
    ) -> str:
        """非流式调用"""
        response = await self.llm.ainvoke(messages, config=config)
        return response.content
    
    async def _stream_completion(
        self,
        messages: List[BaseMessage],
        config: RunnableConfig
    ) -> AsyncGenerator[str, None]:
        """流式调用"""
        async for chunk in self.llm.astream(messages, config=config):
            if hasattr(chunk, 'content') and chunk.content:
                yield chunk.content
    
    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[BaseMessage]:
        """转换消息格式为 LangChain 格式"""
        lc_messages = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:  # user
                lc_messages.append(HumanMessage(content=content))
        
        return lc_messages
    
    def with_structured_output(self, schema: Any):
        """
        结构化输出
        
        LangChain 1.0 使用 ToolStrategy 或 ProviderStrategy
        
        Args:
            schema: Pydantic 模型或 JSON Schema
        
        Returns:
            配置了结构化输出的 LLM
        """
        return self.llm.with_structured_output(schema)
    
    def bind_tools(self, tools: List[Any]):
        """
        绑定工具（用于函数调用）
        
        Args:
            tools: 工具列表（可以是 @tool 装饰的函数或工具定义）
        
        Returns:
            绑定了工具的 LLM
        """
        return self.llm.bind_tools(tools)
    
    @property
    def model_name(self) -> str:
        """获取模型名称"""
        return self.model


class EmbeddingClient:
    """
    Embedding 客户端
    
    基于 LangChain 1.0 的 init_embeddings
    
    支持:
    - OpenAI (text-embedding-3-small, text-embedding-3-large)
    - Google (models/embedding-001)
    - 本地模型 (sentence-transformers)
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        dimensions: Optional[int] = None,
    ):
        """
        初始化 Embedding 客户端
        
        Args:
            provider: 提供商 ("openai", "google", "local", "jedai")
            model: 模型名称
            api_key: API 密钥
            dimensions: 向量维度
        """
        self.provider = provider or settings.EMBEDDING_PROVIDER
        self.model = model or settings.EMBEDDING_MODEL
        self.dimensions = dimensions or settings.EMBEDDING_DIMENSION
        
        # 初始化 Embeddings
        self.embeddings = self._init_embeddings(api_key)
        
        logger.info(f"EmbeddingClient initialized: {self.provider}/{self.model}")
    
    def _init_embeddings(self, api_key: Optional[str]):
        """
        初始化 Embeddings 模型
        
        JedAI 支持多种 embedding 提供商:
        - http: 本地部署 (JEDAI_MODEL_INT_EMBED_2, bge-large-en-v1.5, Qwen3-Embedding-4B, embeddinggemma-300m)
        - gcp: GCP (text-embedding-004, text-embedding-005, gemini-embedding-001 等)
        - aws: AWS (amazon.titan-embed-text-v1, cohere.embed-english-v3 等)
        - azure: Azure (text-embedding-3-small, text-embedding-ada-002)
        """
        if self.provider == "openai":
            return OpenAIEmbeddings(
                model=self.model,
                api_key=api_key or settings.OPENAI_API_KEY or "dummy-key", # Ensure key is present even if dummy for init
                dimensions=self.dimensions,
            )
        elif self.provider == "jedai":
            base_url = settings.JEDAI_API_BASE
            
            # 如果有自定义 embedding URL，直接使用
            if settings.JEDAI_EMBEDDING_URL:
                base_url = settings.JEDAI_EMBEDDING_URL
            else:
                # JedAI Embedding API 使用 /api/copilot/v1/llm/embeddings
                # 参考: https://wiki.cadence.com/cgi-bin/moin.cgi/JedAI/JedAI_Models
                if not base_url.endswith("/embeddings"):
                    base_url = f"{base_url.rstrip('/')}/api/copilot/v1/llm"
            
            # 获取 API key（优先使用缓存的 token）
            jedai_api_key = api_key or settings.JEDAI_API_KEY or get_cached_jedai_token()
            if not jedai_api_key:
                # 尝试登录获取 token（会自动缓存）
                temp_client = LLMClient.__new__(LLMClient)
                jedai_api_key = temp_client._jedai_login() or "dummy-key"
            
            logger.info(f"Initializing JedAI embedding client: {base_url}, model={self.model}, provider={settings.JEDAI_EMBEDDING_PROVIDER}")
            
            # JedAI embedding 需要特殊的 headers 和 extra_body
            default_headers = {
                "Content-Type": "application/json",
                "accept": "*/*",
            }
            if jedai_api_key and jedai_api_key != "dummy-key":
                default_headers["Authorization"] = f"Bearer {jedai_api_key}"
            
            # 根据 embedding provider 构建 extra_body
            extra_body = {}
            embedding_provider = settings.JEDAI_EMBEDDING_PROVIDER.lower()
            if embedding_provider == "gcp":
                extra_body = {
                    "project": settings.JEDAI_GCP_PROJECT,
                    "location": settings.JEDAI_GCP_LOCATION,
                    "provider": "gcp",
                }
            elif embedding_provider == "http":
                extra_body = {"provider": "http"}
            elif embedding_provider == "aws":
                extra_body = {"provider": "aws"}
            elif embedding_provider == "azure":
                extra_body = {"provider": "azure"}
            
            return OpenAIEmbeddings(
                model=self.model,
                api_key=jedai_api_key,
                openai_api_base=base_url,
                dimensions=self.dimensions,
                check_embedding_ctx_length=False,
                http_client=httpx.Client(verify=settings.JEDAI_VERIFY_SSL),
                default_headers=default_headers,
                extra_body=extra_body if extra_body else None,
            )
        else:
            # 尝试使用 init_embeddings
            try:
                return init_embeddings(f"{self.provider}:{self.model}")
            except Exception as e:
                logger.error(f"Failed to init embeddings: {e}")
                raise ValueError(f"Unsupported embedding provider: {self.provider}")
    
    async def embed_text(self, text: str) -> List[float]:
        """
        生成文本的 embedding 向量
        
        Args:
            text: 文本
        
        Returns:
            向量 (List[float])
        """
        return await self.embeddings.aembed_query(text)
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成 embedding 向量
        
        Args:
            texts: 文本列表
        
        Returns:
            向量列表
        """
        return await self.embeddings.aembed_documents(texts)
    
    def embed_text_sync(self, text: str) -> List[float]:
        """同步版本的 embed_text"""
        return self.embeddings.embed_query(text)
    
    def embed_documents_sync(self, texts: List[str]) -> List[List[float]]:
        """同步版本的 embed_documents"""
        return self.embeddings.embed_documents(texts)


# ==================== 全局客户端实例 ====================

_llm_client: Optional[LLMClient] = None
_embedding_client: Optional[EmbeddingClient] = None


def get_llm_client(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> LLMClient:
    """
    获取 LLM 客户端（单例）
    
    Args:
        provider: 提供商（默认从 settings.LLM_PROVIDER 读取）
        model: 模型名称（默认从配置读取）
        **kwargs: 其他参数
    
    Returns:
        LLMClient 实例
    """
    global _llm_client
    if _llm_client is None:
        # 从 settings 读取默认配置
        provider = provider or settings.LLM_PROVIDER
        _llm_client = LLMClient(provider=provider, model=model, **kwargs)
    return _llm_client


def get_embedding_client(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> EmbeddingClient:
    """
    获取 Embedding 客户端（单例）
    
    Args:
        provider: 提供商（默认从 settings.EMBEDDING_PROVIDER 读取）
        model: 模型名称（默认从配置读取）
        **kwargs: 其他参数
    
    Returns:
        EmbeddingClient 实例
    """
    global _embedding_client
    if _embedding_client is None:
        # 从 settings 读取默认配置
        provider = provider or settings.EMBEDDING_PROVIDER
        _embedding_client = EmbeddingClient(provider=provider, model=model, **kwargs)
    return _embedding_client


def reset_clients():
    """重置所有客户端实例（用于测试或配置更新）"""
    global _llm_client, _embedding_client
    _llm_client = None
    _embedding_client = None
    logger.info("LLM and Embedding clients reset")

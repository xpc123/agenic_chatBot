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
from langchain_openai import OpenAIEmbeddings
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableConfig
from loguru import logger

from ..config import settings


class LLMClient:
    """
    LLM 客户端统一接口
    
    基于 LangChain 1.0，使用 init_chat_model 支持:
    - OpenAI (gpt-4o, gpt-4o-mini, gpt-5, etc.)
    - Anthropic (claude-3-5-sonnet, claude-sonnet-4-5, etc.)
    - Google (gemini-1.5-pro, gemini-2.0-flash, etc.)
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
    ```
    """
    
    def __init__(
        self,
        provider: str = "openai",
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
            provider: 提供商 ("openai", "anthropic", "google", "ollama")
            model: 模型名称或完整标识符 (如 "gpt-4o" 或 "openai:gpt-4o")
            temperature: 温度参数 (0.0-2.0)
            api_key: API 密钥
            api_base: API 基础 URL
            max_tokens: 最大 token 数
            timeout: 超时时间（秒）
        """
        self.provider = provider
        self.model = model or settings.OPENAI_MODEL
        self.temperature = temperature if temperature is not None else settings.OPENAI_TEMPERATURE
        self.max_tokens = max_tokens or settings.OPENAI_MAX_TOKENS
        self.timeout = timeout or 30
        
        # 使用 LangChain 1.0 的 init_chat_model 初始化
        self.llm = self._init_llm(api_key, api_base)
        
        logger.info(f"LLMClient initialized: {provider}/{self.model}")
    
    def _init_llm(self, api_key: Optional[str], api_base: Optional[str]) -> BaseChatModel:
        """
        使用 LangChain 1.0 的 init_chat_model 初始化模型
        
        模型标识符格式:
        - 短格式: "gpt-4o" (自动推断为 "openai:gpt-4o")
        - 长格式: "openai:gpt-4o"
        - Claude: "claude-3-5-sonnet" 或 "anthropic:claude-3-5-sonnet"
        """
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
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        dimensions: Optional[int] = None,
    ):
        """
        初始化 Embedding 客户端
        
        Args:
            provider: 提供商 ("openai", "google", "local")
            model: 模型名称
            api_key: API 密钥
            dimensions: 向量维度
        """
        self.provider = provider
        self.model = model or settings.EMBEDDING_MODEL
        self.dimensions = dimensions or settings.EMBEDDING_DIMENSION
        
        # 初始化 Embeddings
        self.embeddings = self._init_embeddings(api_key)
        
        logger.info(f"EmbeddingClient initialized: {provider}/{self.model}")
    
    def _init_embeddings(self, api_key: Optional[str]):
        """初始化 Embeddings 模型"""
        if self.provider == "openai":
            return OpenAIEmbeddings(
                model=self.model,
                api_key=api_key or settings.OPENAI_API_KEY,
                dimensions=self.dimensions,
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
    provider: str = "openai",
    model: Optional[str] = None,
    **kwargs
) -> LLMClient:
    """
    获取 LLM 客户端（单例）
    
    Args:
        provider: 提供商
        model: 模型名称
        **kwargs: 其他参数
    
    Returns:
        LLMClient 实例
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient(provider=provider, model=model, **kwargs)
    return _llm_client


def get_embedding_client(
    provider: str = "openai",
    model: Optional[str] = None,
    **kwargs
) -> EmbeddingClient:
    """
    获取 Embedding 客户端（单例）
    
    Args:
        provider: 提供商
        model: 模型名称
        **kwargs: 其他参数
    
    Returns:
        EmbeddingClient 实例
    """
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = EmbeddingClient(provider=provider, model=model, **kwargs)
    return _embedding_client


def reset_clients():
    """重置所有客户端实例（用于测试或配置更新）"""
    global _llm_client, _embedding_client
    _llm_client = None
    _embedding_client = None
    logger.info("LLM and Embedding clients reset")

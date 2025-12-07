"""
Embedding生成器
"""
from typing import List
from loguru import logger
import numpy as np

from ..config import settings


class EmbeddingGenerator:
    """
    Embedding生成器
    
    支持多种Embedding模型:
    - OpenAI text-embedding-3-small/large
    - Sentence Transformers (本地)
    - Custom models
    """
    
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
        
        # 初始化模型
        self.client = None
        self._initialize_model()
        
        logger.info(f"EmbeddingGenerator initialized with model: {self.model_name}")
    
    def _initialize_model(self):
        """初始化Embedding模型"""
        if self.model_name.startswith("text-embedding"):
            # OpenAI模型
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_API_BASE,
            )
            self.model_type = "openai"
            
        else:
            # Sentence Transformers (本地模型)
            from sentence_transformers import SentenceTransformer
            self.client = SentenceTransformer(self.model_name)
            self.model_type = "sentence_transformer"
    
    async def embed_text(self, text: str) -> List[float]:
        """
        生成单个文本的Embedding
        
        Args:
            text: 输入文本
        
        Returns:
            Embedding向量
        """
        if self.model_type == "openai":
            return await self._embed_openai(text)
        else:
            return await self._embed_local(text)
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成Embedding
        
        Args:
            texts: 文本列表
        
        Returns:
            Embedding向量列表
        """
        if self.model_type == "openai":
            return await self._embed_openai_batch(texts)
        else:
            return await self._embed_local_batch(texts)
    
    async def _embed_openai(self, text: str) -> List[float]:
        """使用OpenAI API生成Embedding"""
        try:
            response = await self.client.embeddings.create(
                model=self.model_name,
                input=text,
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            raise
    
    async def _embed_openai_batch(self, texts: List[str]) -> List[List[float]]:
        """批量OpenAI Embedding"""
        try:
            response = await self.client.embeddings.create(
                model=self.model_name,
                input=texts,
            )
            
            return [item.embedding for item in response.data]
            
        except Exception as e:
            logger.error(f"OpenAI batch embedding failed: {e}")
            raise
    
    async def _embed_local(self, text: str) -> List[float]:
        """使用本地模型生成Embedding"""
        try:
            import asyncio
            
            # 在线程池中执行
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: self.client.encode(text, convert_to_numpy=True)
            )
            
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Local embedding failed: {e}")
            raise
    
    async def _embed_local_batch(self, texts: List[str]) -> List[List[float]]:
        """批量本地Embedding"""
        try:
            import asyncio
            
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self.client.encode(texts, convert_to_numpy=True)
            )
            
            return embeddings.tolist()
            
        except Exception as e:
            logger.error(f"Local batch embedding failed: {e}")
            raise
    
    def compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float],
    ) -> float:
        """
        计算余弦相似度
        
        Args:
            embedding1: 向量1
            embedding2: 向量2
        
        Returns:
            相似度分数 (0-1)
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))


from typing import Optional

# 全局实例
embedding_generator = EmbeddingGenerator()

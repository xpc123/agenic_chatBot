"""
Embedding生成器
"""
from typing import List, Optional
from loguru import logger
import numpy as np

from ..config import settings
from ..llm.client import get_embedding_client


class EmbeddingGenerator:
    """
    Embedding生成器
    
    使用统一的 EmbeddingClient
    """
    
    def __init__(self, model_name: Optional[str] = None):
        self.client = get_embedding_client(model=model_name)
        logger.info(f"EmbeddingGenerator initialized with client: {self.client.provider}/{self.client.model}")
    
    async def embed_text(self, text: str) -> List[float]:
        """
        生成单个文本的Embedding
        
        Args:
            text: 输入文本
        
        Returns:
            Embedding向量
        """
        return await self.client.embed_text(text)
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成Embedding
        
        Args:
            texts: 文本列表
        
        Returns:
            Embedding向量列表
        """
        return await self.client.embed_documents(texts)
    
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


# 全局实例
embedding_generator = EmbeddingGenerator()

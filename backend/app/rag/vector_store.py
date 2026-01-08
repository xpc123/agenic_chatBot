# -*- coding: utf-8 -*-
"""
向量数据库 - Vector Store
支持ChromaDB, FAISS等
"""
from typing import List, Dict, Any, Optional
from loguru import logger
import os

from ..models.document import DocumentChunk
from ..config import settings
from .embeddings import embedding_generator


class VectorStore:
    """
    向量数据库抽象层
    
    支持多种向量数据库:
    - ChromaDB (默认)
    - FAISS
    - Pinecone
    """
    
    def __init__(self, db_type: Optional[str] = None):
        self.db_type = db_type or settings.VECTOR_DB_TYPE
        self.client = None
        self.collection = None
        
        self._initialize_db()
        
        logger.info(f"VectorStore initialized with {self.db_type}")
    
    def _initialize_db(self):
        """初始化向量数据库"""
        if self.db_type == "chroma":
            self._init_chroma()
        elif self.db_type == "faiss":
            self._init_faiss()
        else:
            raise ValueError(f"Unsupported vector DB: {self.db_type}")
    
    def _init_chroma(self):
        """初始化ChromaDB"""
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            
            # 创建持久化客户端
            self.client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                )
            )
            
            # 获取或创建collection
            self.collection = self.client.get_or_create_collection(
                name="documents",
                metadata={"description": "Document chunks for RAG"}
            )
            
            logger.info("ChromaDB initialized")
            
        except Exception as e:
            logger.error(f"ChromaDB initialization failed: {e}")
            raise
    
    def _init_faiss(self):
        """初始化FAISS"""
        try:
            import faiss
            
            # 创建索引
            dimension = settings.EMBEDDING_DIMENSION
            
            # 使用内积相似度 (可以改为L2距离)
            self.index = faiss.IndexFlatIP(dimension)
            
            # 元数据存储 (FAISS只存向量，元数据需要单独存)
            self.metadata_store: Dict[int, Dict] = {}
            
            # 尝试加载已有索引
            # FAISS_INDEX_PATH 应该是目录，实际文件是 index.faiss
            index_dir = settings.FAISS_INDEX_PATH
            index_file = os.path.join(index_dir, "index.faiss")
            
            # 确保目录存在
            os.makedirs(index_dir, exist_ok=True)
            
            if os.path.isfile(index_file):
                self.index = faiss.read_index(index_file)
                logger.info(f"Loaded FAISS index from {index_file} with {self.index.ntotal} vectors")
            else:
                logger.info(f"Created new FAISS index (no existing index found at {index_file})")
            
            logger.info("FAISS initialized")
            
        except Exception as e:
            logger.error(f"FAISS initialization failed: {e}")
            raise
    
    async def add_chunks(self, chunks: List[DocumentChunk]) -> None:
        """
        添加文档块到向量库
        
        Args:
            chunks: 文档块列表
        """
        if not chunks:
            return
        
        logger.info(f"Adding {len(chunks)} chunks to vector store")
        
        # 生成embeddings
        texts = [chunk.content for chunk in chunks]
        embeddings = await embedding_generator.embed_batch(texts)
        
        # 更新chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
        
        # 存储到向量库
        if self.db_type == "chroma":
            await self._add_to_chroma(chunks)
        elif self.db_type == "faiss":
            await self._add_to_faiss(chunks)
    
    async def _add_to_chroma(self, chunks: List[DocumentChunk]) -> None:
        """添加到ChromaDB"""
        try:
            self.collection.add(
                ids=[chunk.id for chunk in chunks],
                embeddings=[chunk.embedding for chunk in chunks],
                documents=[chunk.content for chunk in chunks],
                metadatas=[
                    {
                        "document_id": chunk.document_id,
                        "chunk_index": chunk.chunk_index,
                        **(chunk.metadata or {}),
                    }
                    for chunk in chunks
                ],
            )
            
            logger.info(f"Added {len(chunks)} chunks to ChromaDB")
            
        except Exception as e:
            logger.error(f"ChromaDB add failed: {e}")
            raise
    
    async def _add_to_faiss(self, chunks: List[DocumentChunk]) -> None:
        """添加到FAISS"""
        try:
            import numpy as np
            
            # 转换为numpy数组
            embeddings_array = np.array(
                [chunk.embedding for chunk in chunks],
                dtype='float32'
            )
            
            # 归一化 (用于内积相似度)
            faiss.normalize_L2(embeddings_array)
            
            # 添加到索引
            start_id = self.index.ntotal
            self.index.add(embeddings_array)
            
            # 存储元数据
            for i, chunk in enumerate(chunks):
                self.metadata_store[start_id + i] = {
                    "id": chunk.id,
                    "document_id": chunk.document_id,
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index,
                    "metadata": chunk.metadata,
                }
            
            # 保存索引
            index_dir = settings.FAISS_INDEX_PATH
            index_file = os.path.join(index_dir, "index.faiss")
            os.makedirs(index_dir, exist_ok=True)
            faiss.write_index(self.index, index_file)
            
            logger.info(f"Added {len(chunks)} chunks to FAISS")
            
        except Exception as e:
            logger.error(f"FAISS add failed: {e}")
            raise
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        向量检索
        
        Args:
            query: 查询文本
            top_k: 返回数量
            filters: 过滤条件
        
        Returns:
            检索结果列表
        """
        # 生成查询embedding
        query_embedding = await embedding_generator.embed_text(query)
        
        # 检索
        if self.db_type == "chroma":
            return await self._search_chroma(query_embedding, top_k, filters)
        elif self.db_type == "faiss":
            return await self._search_faiss(query_embedding, top_k, filters)
    
    async def _search_chroma(
        self,
        query_embedding: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """ChromaDB检索"""
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filters,
            )
            
            # 格式化结果
            formatted_results = []
            
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    "id": results['ids'][0][i],
                    "content": results['documents'][0][i],
                    "score": 1 - results['distances'][0][i],  # 转换为相似度
                    "metadata": results['metadatas'][0][i],
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"ChromaDB search failed: {e}")
            return []
    
    async def _search_faiss(
        self,
        query_embedding: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """FAISS检索"""
        try:
            import numpy as np
            import faiss
            
            # 转换为numpy数组
            query_array = np.array([query_embedding], dtype='float32')
            faiss.normalize_L2(query_array)
            
            # 搜索
            scores, indices = self.index.search(query_array, top_k)
            
            # 格式化结果
            formatted_results = []
            
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:  # 无效索引
                    continue
                
                metadata = self.metadata_store.get(int(idx))
                if metadata:
                    formatted_results.append({
                        "id": metadata["id"],
                        "content": metadata["content"],
                        "score": float(score),
                        "metadata": metadata.get("metadata", {}),
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"FAISS search failed: {e}")
            return []
    
    async def delete_document(self, document_id: str) -> None:
        """删除文档的所有块"""
        if self.db_type == "chroma":
            self.collection.delete(
                where={"document_id": document_id}
            )
        elif self.db_type == "faiss":
            # FAISS不支持直接删除，需要重建索引
            logger.warning("FAISS does not support deletion, index rebuild required")
    
    async def get_all_documents(self) -> List[Dict[str, Any]]:
        """
        获取所有文档（用于 BM25 关键词检索）
        
        Returns:
            所有文档的列表
        """
        if self.db_type == "chroma":
            try:
                results = self.collection.get()
                docs = []
                for i, content in enumerate(results.get('documents', [])):
                    docs.append({
                        'content': content,
                        'metadata': results['metadatas'][i] if results.get('metadatas') else {}
                    })
                return docs
            except Exception as e:
                logger.error(f"ChromaDB get_all failed: {e}")
                return []
                
        elif self.db_type == "faiss":
            # 从 metadata_store 获取所有文档
            docs = []
            for idx, metadata in self.metadata_store.items():
                docs.append({
                    'content': metadata.get('content', ''),
                    'metadata': metadata.get('metadata', {})
                })
            return docs
        
        return []


# 全局实例 - 延迟加载
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """获取向量存储实例（延迟加载）"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


# 为了向后兼容，提供模块级别的代理访问
# 但不立即初始化
class _VectorStoreProxy:
    """代理类，延迟访问真实的 VectorStore"""
    def __getattr__(self, name):
        return getattr(get_vector_store(), name)


vector_store = _VectorStoreProxy()

# -*- coding: utf-8 -*-
"""
RAG系统 - 基于LangChain 1.0
使用LangChain的Document、VectorStore、Retriever等组件
"""
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma, FAISS
from langchain_core.vectorstores import VectorStore
from langchain_core.retrievers import BaseRetriever
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger
import os

from ..config import settings
from ..llm import get_embedding_client


class RAGSystem:
    """
    RAG (Retrieval-Augmented Generation) 系统
    
    基于LangChain 1.0实现:
    - 文档加载与分块
    - 向量化存储
    - 语义检索
    - 上下文增强
    """
    
    def __init__(
        self,
        vector_store_type: Optional[str] = None,
        persist_directory: Optional[str] = None,
    ):
        self.vector_store_type = vector_store_type or settings.VECTOR_DB_TYPE
        self.persist_directory = persist_directory
        
        # 获取Embedding客户端
        self.embedding_client = get_embedding_client()
        self.embeddings = self.embedding_client.embeddings
        
        # 初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""],
        )
        
        # 初始化向量存储
        self.vector_store = self._init_vector_store()
        
        # 创建检索器
        self.retriever = self._create_retriever()
        
        logger.info(f"RAGSystem initialized with {self.vector_store_type}")
    
    def _init_vector_store(self) -> VectorStore:
        """初始化向量存储"""
        if self.vector_store_type == "chroma":
            persist_dir = self.persist_directory or settings.CHROMA_PERSIST_DIR
            os.makedirs(persist_dir, exist_ok=True)
            
            # 使用 chromadb.PersistentClient 避免与其他实例冲突
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            
            # 创建或获取已存在的客户端
            client = chromadb.PersistentClient(
                path=persist_dir,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                )
            )
            
            return Chroma(
                client=client,
                embedding_function=self.embeddings,
                collection_name="rag_documents"  # 使用不同的 collection 避免冲突
            )
        
        elif self.vector_store_type == "faiss":
            # FAISS需要先有文档才能初始化
            # 这里返回None，在添加第一个文档时初始化
            return None
        
        else:
            raise ValueError(f"Unsupported vector store: {self.vector_store_type}")
    
    def _create_retriever(self) -> Optional[BaseRetriever]:
        """创建检索器"""
        if not self.vector_store:
            return None
        
        # 使用LangChain的检索器
        return self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={
                "k": settings.TOP_K_RETRIEVAL,
                "score_threshold": settings.SIMILARITY_THRESHOLD,
            }
        )
    
    async def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> List[str]:
        """
        添加文档到向量库
        
        Args:
            texts: 文本列表
            metadatas: 元数据列表
        
        Returns:
            文档ID列表
        """
        # 分块
        all_docs = []
        for i, text in enumerate(texts):
            # 分割文本
            chunks = self.text_splitter.split_text(text)
            
            # 创建Document对象
            metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
            for j, chunk in enumerate(chunks):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        **metadata,
                        "chunk_index": j,
                        "total_chunks": len(chunks),
                    }
                )
                all_docs.append(doc)
        
        logger.info(f"Adding {len(all_docs)} document chunks to vector store")
        
        # 添加到向量库
        if self.vector_store_type == "chroma":
            ids = await self.vector_store.aadd_documents(all_docs)
            return ids
        
        elif self.vector_store_type == "faiss":
            if self.vector_store is None:
                # 首次创建FAISS索引
                self.vector_store = await FAISS.afrom_documents(
                    all_docs,
                    self.embeddings
                )
                self.retriever = self._create_retriever()
            else:
                await self.vector_store.aadd_documents(all_docs)
            
            # FAISS使用数字ID
            return [str(i) for i in range(len(all_docs))]
        
        return []
    
    async def add_document_from_file(
        self,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        从文件添加文档
        
        Args:
            file_path: 文件路径
            metadata: 元数据
        
        Returns:
            文档ID列表
        """
        from langchain_community.document_loaders import (
            TextLoader,
            PDFLoader,
            UnstructuredMarkdownLoader,
        )
        
        # 根据文件类型选择加载器
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == '.pdf':
                loader = PDFLoader(file_path)
            elif ext in ['.md', '.markdown']:
                loader = UnstructuredMarkdownLoader(file_path)
            else:  # .txt等文本文件
                loader = TextLoader(file_path, encoding='utf-8')
            
            # 加载文档
            documents = loader.load()
            
            # 添加额外元数据
            if metadata:
                for doc in documents:
                    doc.metadata.update(metadata)
            
            # 分块并添加
            all_chunks = []
            for doc in documents:
                chunks = self.text_splitter.split_documents([doc])
                all_chunks.extend(chunks)
            
            logger.info(f"Loaded {len(all_chunks)} chunks from {file_path}")
            
            # 添加到向量库
            if self.vector_store_type == "chroma":
                ids = await self.vector_store.aadd_documents(all_chunks)
                return ids
            elif self.vector_store_type == "faiss":
                if self.vector_store is None:
                    self.vector_store = await FAISS.afrom_documents(
                        all_chunks,
                        self.embeddings
                    )
                    self.retriever = self._create_retriever()
                else:
                    await self.vector_store.aadd_documents(all_chunks)
                return [str(i) for i in range(len(all_chunks))]
        
        except Exception as e:
            logger.error(f"Error loading document from {file_path}: {e}")
            raise
    
    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            top_k: 返回文档数量
            filter_metadata: 元数据过滤条件
        
        Returns:
            相关文档列表
        """
        if not self.retriever:
            logger.warning("Retriever not initialized")
            return []
        
        try:
            # 使用检索器检索
            k = top_k or settings.TOP_K_RETRIEVAL
            
            if filter_metadata:
                # 带过滤的检索
                docs = await self.retriever.aget_relevant_documents(
                    query,
                    search_kwargs={
                        "k": k,
                        "filter": filter_metadata
                    }
                )
            else:
                docs = await self.retriever.aget_relevant_documents(query)
            
            # 转换为字典格式
            results = []
            for doc in docs:
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "source": doc.metadata.get("source", "unknown"),
                })
            
            logger.info(f"Retrieved {len(results)} documents for query: {query[:50]}...")
            return results
        
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return []
    
    async def similarity_search_with_score(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[tuple[Document, float]]:
        """
        带相似度分数的检索
        
        Args:
            query: 查询文本
            top_k: 返回文档数量
        
        Returns:
            (文档, 分数)元组列表
        """
        if not self.vector_store:
            return []
        
        try:
            results = await self.vector_store.asimilarity_search_with_score(
                query,
                k=top_k
            )
            return results
        
        except Exception as e:
            logger.error(f"Similarity search error: {e}")
            return []
    
    def delete_documents(self, ids: List[str]) -> bool:
        """
        删除文档
        
        Args:
            ids: 文档ID列表
        
        Returns:
            是否成功
        """
        if not self.vector_store:
            return False
        
        try:
            self.vector_store.delete(ids)
            logger.info(f"Deleted {len(ids)} documents")
            return True
        
        except Exception as e:
            logger.error(f"Delete error: {e}")
            return False
    
    def persist(self):
        """持久化向量库"""
        if self.vector_store_type == "chroma":
            # Chroma自动持久化
            logger.info("Chroma vector store persisted")
        
        elif self.vector_store_type == "faiss" and self.vector_store:
            # FAISS需要手动保存
            save_path = settings.FAISS_INDEX_PATH
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            self.vector_store.save_local(save_path)
            logger.info(f"FAISS vector store saved to {save_path}")


# 全局RAG系统实例
_rag_system: Optional[RAGSystem] = None


def get_rag_system() -> RAGSystem:
    """获取全局RAG系统"""
    global _rag_system
    if _rag_system is None:
        _rag_system = RAGSystem()
    return _rag_system

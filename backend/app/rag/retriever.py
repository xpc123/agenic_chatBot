# -*- coding: utf-8 -*-
"""
RAG检索器 - Retriever
整合文档处理、Embedding和向量检索
"""
from typing import List, Dict, Any, Optional
from loguru import logger
import jieba
from rank_bm25 import BM25Okapi

from ..models.document import Document, DocumentChunk
from ..config import settings
from .document_processor import DocumentProcessor
from .vector_store import vector_store


class RAGRetriever:
    """
    RAG检索器
    
    职责:
    1. 管理文档上传和处理
    2. 执行混合检索 (向量+关键词)
    3. 重排序和过滤
    4. 引用溯源
    """
    
    def __init__(self):
        self.processor = DocumentProcessor()
        self.vector_store = vector_store
        self.top_k = settings.TOP_K_RETRIEVAL
        self.similarity_threshold = settings.SIMILARITY_THRESHOLD
        
        logger.info("RAGRetriever initialized")
    
    async def add_document(
        self,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """
        添加文档到知识库
        
        Args:
            file_path: 文档路径
            metadata: 额外元数据
        
        Returns:
            文档对象
        """
        logger.info(f"Adding document: {file_path}")
        
        # 1. 处理文档
        document, chunks = await self.processor.process_document(
            file_path,
            metadata
        )
        
        # 2. 存储到向量库
        await self.vector_store.add_chunks(chunks)
        
        logger.info(f"Document added: {document.filename}, {len(chunks)} chunks")
        
        return document
    
    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        use_reranking: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            top_k: 返回数量
            filters: 过滤条件
            use_reranking: 是否使用重排序
        
        Returns:
            检索结果列表
        """
        logger.info(f"Retrieving documents for query: {query[:50]}...")
        
        k = top_k or self.top_k
        
        # 1. 向量检索
        results = await self.vector_store.search(
            query=query,
            top_k=k * 2 if use_reranking else k,  # 重排序时先取更多
            filters=filters,
        )
        
        # 2. 过滤低相似度结果
        filtered_results = [
            r for r in results
            if r['score'] >= self.similarity_threshold
        ]
        
        # 3. 重排序 (可选)
        if use_reranking and len(filtered_results) > k:
            filtered_results = await self._rerank(query, filtered_results)
        
        # 4. 截取top_k
        final_results = filtered_results[:k]
        
        # 5. 添加引用信息
        for result in final_results:
            result['citation'] = self._generate_citation(result)
        
        logger.info(f"Retrieved {len(final_results)} relevant documents")
        
        return final_results
    
    async def hybrid_search(
        self,
        query: str,
        top_k: Optional[int] = None,
        alpha: float = 0.7,  # 向量检索权重
    ) -> List[Dict[str, Any]]:
        """
        混合检索: 向量检索 + 关键词检索
        
        Args:
            query: 查询文本
            top_k: 返回数量
            alpha: 向量检索权重 (0-1)
        
        Returns:
            检索结果列表
        """
        k = top_k or self.top_k
        
        # 1. 向量检索
        vector_results = await self.vector_store.search(query, top_k=k)
        
        # 2. 关键词检索 (简化版)
        # TODO: 实现BM25或其他关键词检索
        keyword_results = await self._keyword_search(query, top_k=k)
        
        # 3. 融合结果
        merged_results = self._merge_results(
            vector_results,
            keyword_results,
            alpha=alpha,
        )
        
        return merged_results[:k]
    
    async def _keyword_search(
        self,
        query: str,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """
        BM25 关键词检索
        
        使用 jieba 分词 + BM25 算法
        """
        # 获取所有文档用于 BM25
        all_docs = await self.vector_store.get_all_documents()
        
        if not all_docs:
            return []
        
        # 使用 jieba 分词
        tokenized_corpus = [list(jieba.cut(doc['content'])) for doc in all_docs]
        tokenized_query = list(jieba.cut(query))
        
        # 构建 BM25 索引
        bm25 = BM25Okapi(tokenized_corpus)
        
        # 计算分数
        scores = bm25.get_scores(tokenized_query)
        
        # 获取 top_k 结果
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append({
                    'content': all_docs[idx]['content'],
                    'metadata': all_docs[idx].get('metadata', {}),
                    'score': float(scores[idx]),
                    'search_type': 'keyword'
                })
        
        logger.debug(f"BM25 search returned {len(results)} results")
        return results
    
    def _merge_results(
        self,
        vector_results: List[Dict],
        keyword_results: List[Dict],
        alpha: float,
    ) -> List[Dict]:
        """
        融合向量检索和关键词检索结果
        
        使用 Reciprocal Rank Fusion (RRF) 算法
        RRF(d) = Σ 1/(k + rank(d))  where k=60 is a constant
        """
        k = 60  # RRF 常数
        
        # 计算每个文档的 RRF 分数
        doc_scores = {}  # content_hash -> {score, doc}
        
        # 处理向量检索结果
        for rank, doc in enumerate(vector_results, 1):
            content_hash = hash(doc['content'][:200])
            if content_hash not in doc_scores:
                doc_scores[content_hash] = {'score': 0, 'doc': doc}
            doc_scores[content_hash]['score'] += alpha * (1 / (k + rank))
        
        # 处理关键词检索结果
        for rank, doc in enumerate(keyword_results, 1):
            content_hash = hash(doc['content'][:200])
            if content_hash not in doc_scores:
                doc_scores[content_hash] = {'score': 0, 'doc': doc}
            doc_scores[content_hash]['score'] += (1 - alpha) * (1 / (k + rank))
        
        # 按 RRF 分数排序
        sorted_items = sorted(
            doc_scores.values(),
            key=lambda x: x['score'],
            reverse=True
        )
        
        # 更新分数并返回
        results = []
        for item in sorted_items:
            doc = item['doc'].copy()
            doc['rrf_score'] = item['score']
            doc['search_type'] = 'hybrid'
            results.append(doc)
        
        logger.debug(f"RRF merged {len(vector_results)} vector + {len(keyword_results)} keyword = {len(results)} results")
        return results
    
    async def _rerank(
        self,
        query: str,
        results: List[Dict],
    ) -> List[Dict]:
        """
        使用 LLM 重排序结果
        
        为每个文档计算与查询的相关性分数
        """
        if len(results) <= 1:
            return results
        
        try:
            from ..llm.client import LLMClient
            
            llm_client = LLMClient()
            
            # 构建评分 prompt
            rerank_prompt = f"""请评估以下文档与查询的相关性，为每个文档打分 (0-10)。

查询: {query}

请只返回 JSON 格式的分数列表，例如: [8, 5, 9, 3]

文档列表:
"""
            for i, doc in enumerate(results):
                content_preview = doc['content'][:300]
                rerank_prompt += f"\n--- 文档 {i+1} ---\n{content_preview}\n"
            
            # 调用 LLM
            response = await llm_client.chat([
                {"role": "user", "content": rerank_prompt}
            ])
            
            # 解析分数
            import json
            import re
            
            # 提取 JSON 数组
            match = re.search(r'\[[\d,\s]+\]', response)
            if match:
                scores = json.loads(match.group())
                
                # 应用分数
                for i, doc in enumerate(results):
                    if i < len(scores):
                        doc['rerank_score'] = scores[i]
                    else:
                        doc['rerank_score'] = doc.get('score', 0)
                
                # 按 rerank_score 排序
                results = sorted(results, key=lambda x: x.get('rerank_score', 0), reverse=True)
                logger.info(f"LLM reranking completed: {len(results)} docs reranked")
            else:
                logger.warning("Failed to parse rerank scores, using original order")
                
        except Exception as e:
            logger.error(f"Reranking failed: {e}, using original order")
        
        return results
    
    def _generate_citation(self, result: Dict) -> str:
        """
        生成引用信息
        
        Args:
            result: 检索结果
        
        Returns:
            引用字符串
        """
        metadata = result.get('metadata', {})
        
        document_id = metadata.get('document_id', 'unknown')
        chunk_index = metadata.get('chunk_index', 0)
        
        return f"[文档: {document_id}, 片段: {chunk_index}]"
    
    async def get_context(
        self,
        query: str,
        max_tokens: int = 2000,
    ) -> str:
        """
        获取RAG上下文 (用于注入到prompt)
        
        Args:
            query: 查询文本
            max_tokens: 最大token数
        
        Returns:
            上下文字符串
        """
        results = await self.retrieve(query)
        
        if not results:
            return ""
        
        # 拼接上下文 (简单版: 直接拼接)
        context_parts = ["## 相关知识库内容\n"]
        
        current_tokens = 0
        
        for i, result in enumerate(results, 1):
            content = result['content']
            citation = result.get('citation', '')
            
            # 估算tokens (简化: 1 token ≈ 4 chars)
            estimated_tokens = len(content) // 4
            
            if current_tokens + estimated_tokens > max_tokens:
                break
            
            context_parts.append(f"\n### 引用 {i} {citation}\n{content}\n")
            current_tokens += estimated_tokens
        
        return "\n".join(context_parts)


# 全局实例
retriever = RAGRetriever()

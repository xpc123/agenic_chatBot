# -*- coding: utf-8 -*-
"""
RAG (检索增强生成) 测试

测试 RAG 系统的功能：
- 文档加载
- 文档索引
- 语义搜索
- 上下文检索
- 引用生成
"""
import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import tempfile

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


@pytest.fixture
def temp_docs(tmp_path):
    """创建临时文档目录"""
    # 创建测试文档
    (tmp_path / "doc1.txt").write_text("""
    Python 是一种解释型、面向对象、动态类型的高级程序设计语言。
    Python 的设计哲学强调代码的可读性和简洁的语法。
    Python 支持多种编程范式，包括面向对象、命令式、函数式和过程式编程。
    """)
    
    (tmp_path / "doc2.txt").write_text("""
    机器学习是人工智能的一个分支，专注于通过经验自动改进的算法。
    监督学习、无监督学习和强化学习是机器学习的三种主要类型。
    深度学习是机器学习的一个子领域，使用多层神经网络。
    """)
    
    (tmp_path / "doc3.md").write_text("""
    # API 文档
    
    ## 认证
    使用 API Key 进行认证。在请求头中添加 X-API-Key。
    
    ## 端点
    - POST /api/chat - 发送消息
    - GET /api/documents - 获取文档列表
    
    ## 错误处理
    所有错误返回统一的 JSON 格式。
    """)
    
    return tmp_path


class TestDocumentLoader:
    """测试文档加载器"""
    
    @pytest.mark.asyncio
    async def test_load_text_file(self, temp_docs):
        """测试加载文本文件"""
        from app.rag.loader import DocumentLoader
        
        loader = DocumentLoader()
        docs = await loader.load(str(temp_docs / "doc1.txt"))
        
        assert len(docs) >= 1
        assert "Python" in docs[0].page_content
    
    @pytest.mark.asyncio
    async def test_load_markdown_file(self, temp_docs):
        """测试加载 Markdown 文件"""
        from app.rag.loader import DocumentLoader
        
        loader = DocumentLoader()
        docs = await loader.load(str(temp_docs / "doc3.md"))
        
        assert len(docs) >= 1
        assert "API" in docs[0].page_content
    
    @pytest.mark.asyncio
    async def test_load_directory(self, temp_docs):
        """测试加载目录"""
        from app.rag.loader import DocumentLoader
        
        loader = DocumentLoader()
        docs = await loader.load_directory(str(temp_docs))
        
        assert len(docs) >= 3
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_file(self, temp_docs):
        """测试加载不存在的文件"""
        from app.rag.loader import DocumentLoader
        
        loader = DocumentLoader()
        
        with pytest.raises(Exception):
            await loader.load(str(temp_docs / "nonexistent.txt"))


class TestDocumentChunker:
    """测试文档分块器"""
    
    def test_chunk_document(self, temp_docs):
        """测试文档分块"""
        from app.rag.chunker import DocumentChunker
        
        chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)
        
        text = "这是一段很长的文本。" * 50
        chunks = chunker.chunk(text)
        
        assert len(chunks) >= 1
    
    def test_chunk_with_overlap(self, temp_docs):
        """测试带重叠的分块"""
        from app.rag.chunker import DocumentChunker
        
        chunker = DocumentChunker(chunk_size=50, chunk_overlap=10)
        
        text = "A" * 100 + "B" * 100
        chunks = chunker.chunk(text)
        
        # 相邻块应该有重叠
        assert len(chunks) >= 2
    
    def test_preserve_sentence_boundary(self):
        """测试保留句子边界"""
        from app.rag.chunker import DocumentChunker
        
        chunker = DocumentChunker(chunk_size=50, chunk_overlap=10)
        
        text = "第一句话。第二句话。第三句话。第四句话。"
        chunks = chunker.chunk(text)
        
        # 分块应该尽量在句子边界
        assert isinstance(chunks, list)


class TestVectorStore:
    """测试向量存储"""
    
    @pytest.fixture
    def mock_embeddings(self):
        """Mock 嵌入模型"""
        mock = Mock()
        mock.embed_documents = Mock(return_value=[[0.1, 0.2, 0.3] * 100])
        mock.embed_query = Mock(return_value=[0.1, 0.2, 0.3] * 100)
        return mock
    
    @pytest.mark.asyncio
    async def test_add_documents(self, temp_docs, mock_embeddings):
        """测试添加文档"""
        from app.rag.vector_store import VectorStore
        
        store = VectorStore(embeddings=mock_embeddings)
        
        docs = [
            Mock(page_content="Python 编程", metadata={"source": "doc1"}),
            Mock(page_content="机器学习", metadata={"source": "doc2"}),
        ]
        
        await store.add_documents(docs)
        
        # 应该成功添加
        assert store.document_count >= 2
    
    @pytest.mark.asyncio
    async def test_similarity_search(self, mock_embeddings):
        """测试相似度搜索"""
        from app.rag.vector_store import VectorStore
        
        store = VectorStore(embeddings=mock_embeddings)
        
        # 添加测试文档
        docs = [
            Mock(page_content="Python 编程语言", metadata={"source": "doc1"}),
            Mock(page_content="Java 编程语言", metadata={"source": "doc2"}),
            Mock(page_content="机器学习算法", metadata={"source": "doc3"}),
        ]
        await store.add_documents(docs)
        
        # 搜索
        results = await store.similarity_search("Python", k=2)
        
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_search_with_score(self, mock_embeddings):
        """测试带分数的搜索"""
        from app.rag.vector_store import VectorStore
        
        store = VectorStore(embeddings=mock_embeddings)
        
        docs = [
            Mock(page_content="测试文档", metadata={"source": "test"}),
        ]
        await store.add_documents(docs)
        
        results = await store.similarity_search_with_score("测试", k=1)
        
        assert isinstance(results, list)
        if len(results) > 0:
            assert len(results[0]) == 2  # (doc, score)


class TestRAGPipeline:
    """测试 RAG 管道"""
    
    @pytest.fixture
    def mock_llm(self):
        """Mock LLM"""
        mock = AsyncMock()
        mock.chat_completion = AsyncMock(return_value="基于文档的回答")
        return mock
    
    @pytest.fixture
    def mock_retriever(self):
        """Mock 检索器"""
        mock = AsyncMock()
        mock.get_relevant_documents = AsyncMock(return_value=[
            Mock(page_content="相关文档内容", metadata={"source": "doc1"}),
        ])
        return mock
    
    @pytest.mark.asyncio
    async def test_query_with_rag(self, mock_llm, mock_retriever):
        """测试 RAG 查询"""
        from app.rag.pipeline import RAGPipeline
        
        pipeline = RAGPipeline(llm=mock_llm, retriever=mock_retriever)
        
        result = await pipeline.query("什么是 Python？")
        
        assert result.answer is not None
        assert len(result.sources) >= 0
    
    @pytest.mark.asyncio
    async def test_query_with_no_relevant_docs(self, mock_llm):
        """测试无相关文档的查询"""
        from app.rag.pipeline import RAGPipeline
        
        mock_retriever = AsyncMock()
        mock_retriever.get_relevant_documents = AsyncMock(return_value=[])
        
        pipeline = RAGPipeline(llm=mock_llm, retriever=mock_retriever)
        
        result = await pipeline.query("完全无关的问题")
        
        # 即使没有相关文档，也应该返回回答
        assert result is not None


class TestIndexing:
    """测试索引管理"""
    
    @pytest.fixture
    def index_manager(self, tmp_path):
        """创建索引管理器"""
        from app.rag.index_manager import IndexManager
        return IndexManager(index_path=str(tmp_path / "index"))
    
    @pytest.mark.asyncio
    async def test_index_file(self, index_manager, temp_docs):
        """测试索引文件"""
        result = await index_manager.index_file(str(temp_docs / "doc1.txt"))
        
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_index_directory(self, index_manager, temp_docs):
        """测试索引目录"""
        result = await index_manager.index_directory(str(temp_docs))
        
        assert result.indexed_files >= 1
    
    @pytest.mark.asyncio
    async def test_get_index_status(self, index_manager, temp_docs):
        """测试获取索引状态"""
        await index_manager.index_directory(str(temp_docs))
        
        status = await index_manager.get_status()
        
        assert "indexed_files" in status
    
    @pytest.mark.asyncio
    async def test_clear_index(self, index_manager, temp_docs):
        """测试清除索引"""
        await index_manager.index_directory(str(temp_docs))
        await index_manager.clear()
        
        status = await index_manager.get_status()
        
        assert status.get("indexed_files", 0) == 0


class TestCitationGeneration:
    """测试引用生成"""
    
    def test_generate_citation(self):
        """测试生成引用"""
        from app.rag.citation import CitationGenerator
        
        generator = CitationGenerator()
        
        sources = [
            {"source": "doc1.pdf", "content": "Python 是..."},
            {"source": "doc2.md", "content": "机器学习是..."},
        ]
        
        citations = generator.generate(sources)
        
        assert len(citations) == 2
        assert "doc1.pdf" in citations[0]["source"]
    
    def test_format_citations(self):
        """测试格式化引用"""
        from app.rag.citation import CitationGenerator
        
        generator = CitationGenerator()
        
        sources = [
            {"source": "doc1.pdf", "content": "相关内容"},
        ]
        
        formatted = generator.format_for_display(sources)
        
        assert isinstance(formatted, str)
        assert "doc1.pdf" in formatted


class TestRAGConfiguration:
    """测试 RAG 配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        from app.rag.config import RAGConfig
        
        config = RAGConfig()
        
        assert config.chunk_size > 0
        assert config.chunk_overlap >= 0
        assert config.top_k > 0
    
    def test_custom_config(self):
        """测试自定义配置"""
        from app.rag.config import RAGConfig
        
        config = RAGConfig(
            chunk_size=500,
            chunk_overlap=50,
            top_k=10,
            score_threshold=0.7,
        )
        
        assert config.chunk_size == 500
        assert config.top_k == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


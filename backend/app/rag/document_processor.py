"""
文档处理器 - Document Processor
支持多种文档格式的解析和分块
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger
import hashlib
from datetime import datetime

from ..models.document import Document, DocumentChunk
from ..config import settings


class DocumentProcessor:
    """
    文档处理器
    
    职责:
    1. 解析多种文档格式 (PDF, DOCX, TXT, MD, HTML)
    2. 智能文档分块 (Chunking)
    3. 提取元数据
    """
    
    def __init__(self):
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP
        
        logger.info("DocumentProcessor initialized")
    
    async def process_document(
        self,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """
        处理文档
        
        Args:
            file_path: 文档路径
            metadata: 额外元数据
        
        Returns:
            文档对象
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # 生成文档ID
        doc_id = self._generate_doc_id(file_path)
        
        # 提取文本
        text = await self._extract_text(file_path)
        
        # 分块
        chunks = await self._chunk_text(text, doc_id)
        
        # 创建文档对象
        document = Document(
            id=doc_id,
            filename=path.name,
            file_type=path.suffix,
            file_size=path.stat().st_size,
            processed=True,
            chunk_count=len(chunks),
            metadata=metadata or {},
        )
        
        logger.info(f"Processed document: {path.name}, {len(chunks)} chunks")
        
        return document, chunks
    
    async def _extract_text(self, file_path: str) -> str:
        """提取文档文本"""
        path = Path(file_path)
        extension = path.suffix.lower()
        
        if extension == '.pdf':
            return await self._extract_pdf(file_path)
        elif extension == '.docx':
            return await self._extract_docx(file_path)
        elif extension in ['.txt', '.md']:
            return await self._extract_text_file(file_path)
        elif extension == '.html':
            return await self._extract_html(file_path)
        else:
            raise ValueError(f"Unsupported file type: {extension}")
    
    async def _extract_pdf(self, file_path: str) -> str:
        """提取PDF文本"""
        try:
            from pypdf import PdfReader
            
            reader = PdfReader(file_path)
            text = ""
            
            for page in reader.pages:
                text += page.extract_text() + "\n\n"
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            raise
    
    async def _extract_docx(self, file_path: str) -> str:
        """提取DOCX文本"""
        try:
            from docx import Document as DocxDocument
            
            doc = DocxDocument(file_path)
            text = "\n\n".join([para.text for para in doc.paragraphs])
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            raise
    
    async def _extract_text_file(self, file_path: str) -> str:
        """提取纯文本"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            raise
    
    async def _extract_html(self, file_path: str) -> str:
        """提取HTML文本"""
        try:
            from bs4 import BeautifulSoup
            
            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            
            # 移除script和style标签
            for script in soup(["script", "style"]):
                script.decompose()
            
            return soup.get_text(separator='\n\n').strip()
            
        except Exception as e:
            logger.error(f"HTML extraction failed: {e}")
            raise
    
    async def _chunk_text(
        self,
        text: str,
        doc_id: str,
    ) -> List[DocumentChunk]:
        """
        智能文本分块
        
        使用滑动窗口和重叠来保持上下文连贯性
        """
        chunks = []
        
        # 简单的字符级分块 (可以优化为语义分块)
        text_length = len(text)
        chunk_index = 0
        
        for start in range(0, text_length, self.chunk_size - self.chunk_overlap):
            end = min(start + self.chunk_size, text_length)
            chunk_text = text[start:end].strip()
            
            if not chunk_text:
                continue
            
            chunk = DocumentChunk(
                id=f"{doc_id}_chunk_{chunk_index}",
                document_id=doc_id,
                content=chunk_text,
                chunk_index=chunk_index,
                metadata={
                    "start_char": start,
                    "end_char": end,
                    "length": len(chunk_text),
                }
            )
            
            chunks.append(chunk)
            chunk_index += 1
        
        return chunks
    
    def _generate_doc_id(self, file_path: str) -> str:
        """生成文档ID"""
        path = Path(file_path)
        content = f"{path.name}_{path.stat().st_mtime}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    async def chunk_with_semantic_splitting(
        self,
        text: str,
        doc_id: str,
    ) -> List[DocumentChunk]:
        """
        语义分块 (高级功能)
        
        基于段落、句子边界进行智能分块
        """
        # TODO: 实现基于语义的分块
        # 可以使用nltk、spacy等库
        
        return await self._chunk_text(text, doc_id)

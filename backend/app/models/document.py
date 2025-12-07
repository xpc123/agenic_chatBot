"""
文档相关数据模型
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class Document(BaseModel):
    """文档"""
    id: str
    filename: str
    file_type: str
    file_size: int
    upload_time: datetime = Field(default_factory=datetime.now)
    processed: bool = False
    chunk_count: int = 0
    metadata: Optional[Dict[str, Any]] = None
    

class DocumentChunk(BaseModel):
    """文档块"""
    id: str
    document_id: str
    content: str
    chunk_index: int
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None
    

class DocumentUploadRequest(BaseModel):
    """文档上传请求"""
    filename: str
    file_type: str
    metadata: Optional[Dict[str, Any]] = None
    

class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    document_id: str
    filename: str
    status: str
    message: str
    

class DocumentSearchRequest(BaseModel):
    """文档搜索请求"""
    query: str
    top_k: int = 5
    document_ids: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    

class DocumentSearchResult(BaseModel):
    """文档搜索结果"""
    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: Optional[Dict[str, Any]] = None

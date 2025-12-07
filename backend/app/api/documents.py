"""
文档管理API路由
"""
from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from typing import List, Optional
from loguru import logger
import os
import uuid
from pathlib import Path

from ..models.document import (
    DocumentUploadResponse,
    DocumentSearchRequest,
    Document,
)
from ..rag import retriever
from ..config import settings

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
):
    """
    上传文档
    
    Args:
        file: 上传的文件
        metadata: 元数据 (JSON字符串)
    
    Returns:
        上传响应
    """
    try:
        # 验证文件类型
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}"
            )
        
        # 生成文件ID和路径
        doc_id = str(uuid.uuid4())[:8]
        filename = f"{doc_id}_{file.filename}"
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        
        # 确保目录存在
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        # 保存文件
        with open(file_path, 'wb') as f:
            content = await file.read()
            
            # 检查文件大小
            if len(content) > settings.MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"文件太大，最大 {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB"
                )
            
            f.write(content)
        
        # 处理文档
        import json
        metadata_dict = json.loads(metadata) if metadata else {}
        
        document = await retriever.add_document(file_path, metadata_dict)
        
        logger.info(f"Document uploaded: {filename}")
        
        return DocumentUploadResponse(
            document_id=document.id,
            filename=document.filename,
            status="success",
            message=f"文档上传成功，已处理 {document.chunk_count} 个文档块",
        )
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_documents(request: DocumentSearchRequest):
    """
    搜索文档
    
    Args:
        request: 搜索请求
    
    Returns:
        搜索结果
    """
    try:
        results = await retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
        )
        
        return {
            "query": request.query,
            "results": results,
            "count": len(results),
        }
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_documents():
    """
    列出所有文档
    
    Returns:
        文档列表
    """
    try:
        # TODO: 实现文档列表查询
        # 需要维护文档索引
        
        return {
            "documents": [],
            "count": 0,
        }
        
    except Exception as e:
        logger.error(f"List error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """
    删除文档
    
    Args:
        document_id: 文档ID
    """
    try:
        from ..rag import vector_store
        
        await vector_store.delete_document(document_id)
        
        return {"message": "文档删除成功"}
        
    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

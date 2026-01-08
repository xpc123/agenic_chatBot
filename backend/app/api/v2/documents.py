# -*- coding: utf-8 -*-
"""
Documents API v2 - 文档管理接口

端点:
- POST   /documents/upload    - 上传文档
- POST   /documents/search    - 搜索文档
- GET    /documents/list      - 列出文档
- GET    /documents/{id}      - 获取文档详情
- DELETE /documents/{id}      - 删除文档
"""
from fastapi import APIRouter, File, UploadFile, HTTPException, Form, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from loguru import logger
import os
import uuid
import json
from pathlib import Path
from datetime import datetime

from ...config import settings
from ...rag import retriever
from ..middleware import get_current_user, AuthenticatedUser

router = APIRouter(prefix="/documents", tags=["documents-v2"])


# ==================== 请求/响应模型 ====================

class DocumentSearchRequest(BaseModel):
    """文档搜索请求"""
    query: str = Field(..., description="搜索查询")
    top_k: int = Field(5, description="返回结果数量")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    document_id: str
    filename: str
    status: str
    message: str
    chunk_count: int = 0


# ==================== 工具函数 ====================

DOCUMENT_INDEX_FILE = os.path.join(settings.UPLOAD_DIR, ".document_index.json")


def _load_document_index() -> Dict[str, Dict[str, Any]]:
    """加载文档索引"""
    if os.path.exists(DOCUMENT_INDEX_FILE):
        try:
            with open(DOCUMENT_INDEX_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load document index: {e}")
    return {}


def _save_document_index(index: Dict[str, Dict[str, Any]]) -> None:
    """保存文档索引"""
    try:
        os.makedirs(os.path.dirname(DOCUMENT_INDEX_FILE), exist_ok=True)
        with open(DOCUMENT_INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to save document index: {e}")


# ==================== API 端点 ====================

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    上传文档
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
        content = await file.read()
        
        # 检查文件大小
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件太大，最大 {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB"
            )
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # 处理文档
        metadata_dict = json.loads(metadata) if metadata else {}
        metadata_dict["uploaded_by"] = user.user_id
        
        document = await retriever.add_document(file_path, metadata_dict)
        
        # 更新文档索引
        doc_index = _load_document_index()
        doc_index[document.id] = {
            "id": document.id,
            "filename": document.filename,
            "file_type": document.file_type,
            "file_size": document.file_size,
            "file_path": file_path,
            "upload_time": datetime.now().isoformat(),
            "uploaded_by": user.user_id,
            "processed": True,
            "chunk_count": document.chunk_count,
            "metadata": metadata_dict,
        }
        _save_document_index(doc_index)
        
        logger.info(f"Document uploaded: {filename} by {user.user_id}")
        
        return DocumentUploadResponse(
            document_id=document.id,
            filename=document.filename,
            status="success",
            message=f"文档上传成功，已处理 {document.chunk_count} 个文档块",
            chunk_count=document.chunk_count,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_documents(
    request: DocumentSearchRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    搜索文档
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
async def list_documents(
    page: int = 1,
    page_size: int = 20,
    file_type: Optional[str] = None,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    列出所有文档
    """
    try:
        doc_index = _load_document_index()
        documents = list(doc_index.values())
        
        # 按文件类型过滤
        if file_type:
            documents = [d for d in documents if d.get("file_type") == file_type]
        
        # 按上传时间倒序排列
        documents.sort(key=lambda x: x.get("upload_time", ""), reverse=True)
        
        # 分页
        total = len(documents)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_docs = documents[start:end]
        
        return {
            "documents": paginated_docs,
            "count": len(paginated_docs),
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }
        
    except Exception as e:
        logger.error(f"List error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    获取单个文档信息
    """
    try:
        doc_index = _load_document_index()
        
        if document_id not in doc_index:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        return doc_index[document_id]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    删除文档
    """
    try:
        from ...rag import vector_store
        
        # 从向量库删除
        await vector_store.delete_document(document_id)
        
        # 从索引删除
        doc_index = _load_document_index()
        doc_info = doc_index.pop(document_id, None)
        _save_document_index(doc_index)
        
        # 删除原文件
        if doc_info and doc_info.get("file_path"):
            file_path = doc_info["file_path"]
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
        
        return {"message": "文档删除成功", "document_id": document_id}
        
    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


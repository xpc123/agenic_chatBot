# -*- coding: utf-8 -*-
"""
Batch API v2 - 批量操作接口

端点:
- POST /batch/chat       - 批量对话
- POST /batch/documents  - 批量上传文档
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from loguru import logger
import asyncio
import uuid

from ...core.cursor_style_orchestrator import CursorStyleOrchestrator
from ...llm import get_llm_client
from ..middleware import get_current_user, AuthenticatedUser

router = APIRouter(prefix="/batch", tags=["batch-v2"])


# ==================== Pydantic Models ====================

class BatchChatRequest(BaseModel):
    """批量聊天请求中的单个请求"""
    message: str = Field(..., description="用户消息")
    session_id: Optional[str] = Field(None, description="会话 ID")
    use_rag: bool = Field(True, description="是否使用 RAG")


class BatchChatRequestBody(BaseModel):
    """批量聊天请求体"""
    requests: List[BatchChatRequest] = Field(..., description="请求列表")
    parallel: bool = Field(True, description="是否并行处理")
    max_concurrency: int = Field(5, description="最大并发数")


class BatchDocumentRequest(BaseModel):
    """批量文档请求中的单个文档"""
    content: str = Field(..., description="文档内容")
    filename: str = Field(..., description="文件名")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class BatchDocumentRequestBody(BaseModel):
    """批量文档请求体"""
    documents: List[BatchDocumentRequest] = Field(..., description="文档列表")


# ==================== 全局编排器 ====================

_orchestrator: Optional[CursorStyleOrchestrator] = None


def get_batch_orchestrator() -> CursorStyleOrchestrator:
    """获取编排器"""
    global _orchestrator
    
    if _orchestrator is None:
        try:
            llm_client = get_llm_client()
            
            from ...core.practical_tools import get_practical_tools
            tools = get_practical_tools()
            
            _orchestrator = CursorStyleOrchestrator(
                llm_client=llm_client,
                tools=tools,
                enable_rag=True,
                enable_skills=True,
                enable_memory=True,
                enable_preferences=True,
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise HTTPException(status_code=503, detail=str(e))
    
    return _orchestrator


# ==================== API 端点 ====================

@router.post("/chat")
async def batch_chat(
    body: BatchChatRequestBody,
    user: AuthenticatedUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    批量对话
    
    支持并行和串行两种模式。
    
    Args:
        body: 批量请求体
        
    Returns:
        results: 响应列表
        success_count: 成功数量
        error_count: 错误数量
    """
    try:
        orchestrator = get_batch_orchestrator()
        
        results = []
        success_count = 0
        error_count = 0
        
        if body.parallel:
            # 并行处理（使用信号量限制并发）
            semaphore = asyncio.Semaphore(body.max_concurrency)
            
            async def process_request(req: BatchChatRequest, index: int):
                async with semaphore:
                    try:
                        session_id = req.session_id or str(uuid.uuid4())
                        response = await orchestrator.chat(
                            message=req.message,
                            session_id=session_id,
                        )
                        return {
                            "index": index,
                            "success": True,
                            "message": response.content,
                            "session_id": session_id,
                            "used_tools": response.used_tools,
                        }
                    except Exception as e:
                        return {
                            "index": index,
                            "success": False,
                            "error": str(e),
                        }
            
            tasks = [
                process_request(req, i)
                for i, req in enumerate(body.requests)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # 按原始顺序排序
            results = sorted(results, key=lambda x: x["index"])
            
        else:
            # 串行处理
            for i, req in enumerate(body.requests):
                try:
                    session_id = req.session_id or str(uuid.uuid4())
                    response = await orchestrator.chat(
                        message=req.message,
                        session_id=session_id,
                    )
                    results.append({
                        "index": i,
                        "success": True,
                        "message": response.content,
                        "session_id": session_id,
                        "used_tools": response.used_tools,
                    })
                except Exception as e:
                    results.append({
                        "index": i,
                        "success": False,
                        "error": str(e),
                    })
        
        # 统计
        for r in results:
            if r.get("success"):
                success_count += 1
            else:
                error_count += 1
        
        return {
            "results": results,
            "total": len(body.requests),
            "success_count": success_count,
            "error_count": error_count,
        }
        
    except Exception as e:
        logger.exception(f"Batch chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents")
async def batch_upload_documents(
    body: BatchDocumentRequestBody,
    user: AuthenticatedUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    批量上传文档（文本内容）
    
    用于批量上传文本文档到 RAG 系统。
    
    Args:
        body: 批量文档请求体
        
    Returns:
        results: 上传结果列表
        success_count: 成功数量
        error_count: 错误数量
    """
    try:
        from ...rag.document_processor import DocumentProcessor
        from ...rag.vector_store import VectorStore
        
        processor = DocumentProcessor()
        vector_store = VectorStore()
        
        results = []
        success_count = 0
        error_count = 0
        
        for i, doc in enumerate(body.documents):
            try:
                # 处理文本内容
                metadata = doc.metadata or {}
                metadata["filename"] = doc.filename
                metadata["uploaded_by"] = user.user_id
                
                # 分块处理
                chunks = processor.process_text(
                    doc.content,
                    metadata=metadata,
                )
                
                if chunks:
                    # 存储到向量库
                    await vector_store.add_documents(chunks)
                    
                    results.append({
                        "index": i,
                        "success": True,
                        "filename": doc.filename,
                        "chunk_count": len(chunks),
                    })
                    success_count += 1
                else:
                    results.append({
                        "index": i,
                        "success": False,
                        "filename": doc.filename,
                        "error": "No chunks generated",
                    })
                    error_count += 1
                    
            except Exception as e:
                results.append({
                    "index": i,
                    "success": False,
                    "filename": doc.filename,
                    "error": str(e),
                })
                error_count += 1
        
        return {
            "results": results,
            "total": len(body.documents),
            "success_count": success_count,
            "error_count": error_count,
        }
        
    except Exception as e:
        logger.exception(f"Batch upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


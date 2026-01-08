# -*- coding: utf-8 -*-
"""
Tools API v2 - 工具管理接口

端点:
- GET  /tools/list              - 列出所有工具
- GET  /tools/health            - 工具健康状态
- GET  /tools/servers           - 列出 MCP 服务器
- POST /tools/servers/register  - 注册 MCP 服务器
- POST /tools/servers/{server_name}/reload - 重新加载服务器
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from loguru import logger

from ...models.tool import MCPServer, MCPServerStatus
from ...mcp import mcp_registry
from ..middleware import get_current_user, AuthenticatedUser

router = APIRouter(prefix="/tools", tags=["tools-v2"])


class ServerRegisterRequest(BaseModel):
    """注册服务器请求"""
    name: str
    url: str
    description: Optional[str] = None


@router.get("/list")
async def list_tools(
    server_name: Optional[str] = None,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    列出所有可用工具
    
    Args:
        server_name: 过滤服务器名称 (可选)
    
    Returns:
        工具列表
    """
    try:
        tools = mcp_registry.list_tools(server_name=server_name)
        
        return {
            "tools": [tool.model_dump() for tool in tools],
            "total": len(tools),
        }
        
    except Exception as e:
        logger.error(f"List tools error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to list tools", "message": str(e)}
        )


@router.get("/health")
async def tools_health(user: AuthenticatedUser = Depends(get_current_user)):
    """
    工具健康状态
    """
    try:
        servers = mcp_registry.list_servers()
        
        return {
            "status": "ok" if servers else "no_servers",
            "servers": [
                {
                    "name": s.name,
                    "enabled": s.enabled,
                    "tool_count": len(s.tools),
                }
                for s in servers
            ],
            "total_tools": sum(len(s.tools) for s in servers),
        }
        
    except Exception as e:
        logger.error(f"Tools health error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/servers")
async def list_servers(user: AuthenticatedUser = Depends(get_current_user)):
    """
    列出 MCP 服务器
    """
    try:
        servers = mcp_registry.list_servers()
        
        return {
            "servers": [
                {
                    "name": s.name,
                    "url": s.url,
                    "enabled": s.enabled,
                    "tool_count": len(s.tools),
                    "description": s.description,
                }
                for s in servers
            ],
            "total": len(servers),
        }
        
    except Exception as e:
        logger.error(f"List servers error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to list servers", "message": str(e)}
        )


@router.post("/servers/register")
async def register_server(
    request: ServerRegisterRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    注册新的 MCP 服务器
    """
    try:
        await mcp_registry.register_server(
            name=request.name,
            url=request.url,
            description=request.description,
        )
        
        return {
            "message": f"Server '{request.name}' registered successfully",
            "server": request.name,
        }
        
    except Exception as e:
        logger.error(f"Register server error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to register server", "message": str(e)}
        )


@router.post("/servers/{server_name}/reload")
async def reload_server(
    server_name: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    重新加载服务器工具
    """
    try:
        # 尝试重新连接并刷新工具列表
        server = mcp_registry.get_server(server_name)
        if not server:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Server '{server_name}' not found"}
            )
        
        await mcp_registry.reload_server(server_name)
        
        return {
            "message": f"Server '{server_name}' reloaded",
            "server": server_name,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reload server error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to reload server", "message": str(e)}
        )


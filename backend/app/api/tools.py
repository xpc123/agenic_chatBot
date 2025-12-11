# -*- coding: utf-8 -*-
"""
工具管理API路由
"""
from fastapi import APIRouter, HTTPException
from typing import List
from loguru import logger

from ..models.tool import MCPServer, MCPServerStatus
from ..mcp import mcp_registry

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/list")
async def list_tools(server_name: str = None):
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
            "count": len(tools),
        }
        
    except Exception as e:
        logger.error(f"List tools error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/servers")
async def list_servers():
    """
    列出所有MCP服务器
    
    Returns:
        服务器列表
    """
    try:
        servers = mcp_registry.list_servers()
        
        return {
            "servers": [server.model_dump() for server in servers],
            "count": len(servers),
        }
        
    except Exception as e:
        logger.error(f"List servers error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def check_health():
    """
    检查所有服务器健康状态
    
    Returns:
        健康状态列表
    """
    try:
        statuses = await mcp_registry.health_check()
        
        return {
            "statuses": [status.model_dump() for status in statuses],
            "count": len(statuses),
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/servers/{server_name}/reload")
async def reload_server(server_name: str):
    """
    重新加载MCP服务器
    
    Args:
        server_name: 服务器名称
    """
    try:
        success = await mcp_registry.reload_server(server_name)
        
        if success:
            return {"message": f"服务器 {server_name} 重新加载成功"}
        else:
            raise HTTPException(status_code=400, detail="重新加载失败")
            
    except Exception as e:
        logger.error(f"Reload server error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/servers/register", response_model=dict)
async def register_server(server: MCPServer):
    """
    注册新的MCP服务器
    
    Args:
        server: 服务器配置
    """
    try:
        await mcp_registry.register_server(server)
        
        return {"message": f"服务器 {server.name} 注册成功"}
        
    except Exception as e:
        logger.error(f"Register server error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# -*- coding: utf-8 -*-
"""
MCP客户端 - Client
与MCP Server通信的客户端实现
"""
from typing import Dict, List, Any, Optional
from loguru import logger
import httpx
import asyncio

from ..config import settings


class MCPClient:
    """
    MCP协议客户端
    
    通过HTTP/WebSocket与MCP Server通信
    """
    
    def __init__(
        self,
        url: str,
        auth: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ):
        self.url = url.rstrip('/')
        self.auth = auth
        self.timeout = timeout
        self.connected = False
        
        # HTTP客户端
        self.http_client: Optional[httpx.AsyncClient] = None
    
    async def connect(self) -> None:
        """建立连接"""
        headers = {}
        
        if self.auth:
            # 添加认证头
            if 'api_key' in self.auth:
                headers['Authorization'] = f"Bearer {self.auth['api_key']}"
        
        self.http_client = httpx.AsyncClient(
            base_url=self.url,
            headers=headers,
            timeout=self.timeout,
        )
        
        # 测试连接
        try:
            await self.ping()
            self.connected = True
            logger.info(f"Connected to MCP server: {self.url}")
        except Exception as e:
            logger.error(f"Failed to connect to {self.url}: {e}")
            raise
    
    async def disconnect(self) -> None:
        """断开连接"""
        if self.http_client:
            await self.http_client.aclose()
            self.connected = False
            logger.info(f"Disconnected from {self.url}")
    
    async def ping(self) -> bool:
        """
        Ping服务器
        
        Returns:
            是否在线
        """
        try:
            response = await self.http_client.get("/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ping failed: {e}")
            return False
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        获取服务器提供的所有工具
        
        Returns:
            工具列表
        """
        try:
            response = await self.http_client.get("/tools")
            response.raise_for_status()
            
            data = response.json()
            return data.get('tools', [])
            
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """
        调用工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
        
        Returns:
            工具执行结果
        """
        try:
            response = await self.http_client.post(
                f"/tools/{tool_name}/execute",
                json={"arguments": arguments},
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success'):
                return data.get('result')
            else:
                raise Exception(data.get('error', 'Tool execution failed'))
                
        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            raise
    
    async def get_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """
        获取工具的JSON Schema
        
        Args:
            tool_name: 工具名称
        
        Returns:
            工具schema
        """
        try:
            response = await self.http_client.get(f"/tools/{tool_name}/schema")
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get tool schema: {e}")
            return {}
    
    async def batch_call(
        self,
        calls: List[Dict[str, Any]],
    ) -> List[Any]:
        """
        批量调用工具
        
        Args:
            calls: 调用列表，每个包含 tool_name 和 arguments
        
        Returns:
            结果列表
        """
        tasks = [
            self.call_tool(call['tool_name'], call['arguments'])
            for call in calls
        ]
        
        return await asyncio.gather(*tasks, return_exceptions=True)

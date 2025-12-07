"""
MCP工具注册中心 - Tool Registry
管理所有可用的MCP工具
"""
from typing import Dict, List, Optional, Any
from loguru import logger
import json
import os

from ..models.tool import Tool, MCPServer, MCPServerStatus
from ..config import settings


class MCPRegistry:
    """
    MCP工具注册中心
    
    职责:
    1. 加载和管理MCP Servers
    2. 注册工具
    3. 工具发现和查询
    4. 健康检查
    """
    
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self.tools: Dict[str, Tool] = {}  # tool_name -> Tool
        self.server_clients: Dict[str, Any] = {}  # server_name -> client
        
        logger.info("MCPRegistry initialized")
    
    async def load_servers(self, config_path: Optional[str] = None) -> None:
        """
        从配置文件加载MCP Servers
        
        Args:
            config_path: 配置文件路径
        """
        config_file = config_path or settings.MCP_SERVERS_CONFIG
        
        if not os.path.exists(config_file):
            logger.warning(f"MCP config file not found: {config_file}")
            return
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            servers_config = config.get('servers', [])
            
            for server_config in servers_config:
                await self.register_server(MCPServer(**server_config))
            
            logger.info(f"Loaded {len(self.servers)} MCP servers")
            
        except Exception as e:
            logger.error(f"Failed to load MCP servers: {e}")
    
    async def register_server(self, server: MCPServer) -> None:
        """
        注册MCP Server
        
        Args:
            server: MCP服务器配置
        """
        logger.info(f"Registering MCP server: {server.name}")
        
        # 存储服务器
        self.servers[server.name] = server
        
        # 连接到服务器并发现工具
        try:
            client = await self._connect_to_server(server)
            self.server_clients[server.name] = client
            
            # 发现工具
            tools = await self._discover_tools(client, server.name)
            
            # 注册工具
            for tool in tools:
                self.tools[tool.name] = tool
            
            server.tools = tools
            
            logger.info(
                f"Server {server.name} registered with {len(tools)} tools"
            )
            
        except Exception as e:
            logger.error(f"Failed to register server {server.name}: {e}")
            server.enabled = False
    
    async def _connect_to_server(self, server: MCPServer) -> Any:
        """
        连接到MCP Server
        
        Args:
            server: MCP服务器配置
        
        Returns:
            MCP客户端
        """
        from .client import MCPClient
        
        client = MCPClient(
            url=server.url,
            auth=server.auth,
            timeout=settings.MCP_TIMEOUT,
        )
        
        await client.connect()
        
        return client
    
    async def _discover_tools(
        self,
        client: Any,
        server_name: str,
    ) -> List[Tool]:
        """
        从服务器发现工具
        
        Args:
            client: MCP客户端
            server_name: 服务器名称
        
        Returns:
            工具列表
        """
        try:
            tools_data = await client.list_tools()
            
            tools = []
            for tool_data in tools_data:
                tool = Tool(
                    name=tool_data['name'],
                    description=tool_data['description'],
                    parameters=tool_data.get('parameters', {}),
                    server_name=server_name,
                )
                tools.append(tool)
            
            return tools
            
        except Exception as e:
            logger.error(f"Tool discovery failed for {server_name}: {e}")
            return []
    
    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """
        获取工具
        
        Args:
            tool_name: 工具名称
        
        Returns:
            工具对象
        """
        return self.tools.get(tool_name)
    
    def get_server_client(self, server_name: str) -> Optional[Any]:
        """
        获取服务器客户端
        
        Args:
            server_name: 服务器名称
        
        Returns:
            MCP客户端
        """
        return self.server_clients.get(server_name)
    
    def list_tools(
        self,
        server_name: Optional[str] = None,
        enabled_only: bool = True,
    ) -> List[Tool]:
        """
        列出所有工具
        
        Args:
            server_name: 过滤服务器名称
            enabled_only: 只返回启用的工具
        
        Returns:
            工具列表
        """
        tools = list(self.tools.values())
        
        if server_name:
            tools = [t for t in tools if t.server_name == server_name]
        
        if enabled_only:
            tools = [t for t in tools if t.enabled]
        
        return tools
    
    def list_servers(self, enabled_only: bool = True) -> List[MCPServer]:
        """
        列出所有服务器
        
        Args:
            enabled_only: 只返回启用的服务器
        
        Returns:
            服务器列表
        """
        servers = list(self.servers.values())
        
        if enabled_only:
            servers = [s for s in servers if s.enabled]
        
        return servers
    
    async def health_check(self) -> List[MCPServerStatus]:
        """
        检查所有服务器健康状态
        
        Returns:
            状态列表
        """
        statuses = []
        
        for server_name, server in self.servers.items():
            try:
                client = self.server_clients.get(server_name)
                
                if not client:
                    status = MCPServerStatus(
                        name=server_name,
                        status="offline",
                        tool_count=0,
                        error_message="Client not connected",
                    )
                else:
                    # Ping服务器
                    await client.ping()
                    
                    status = MCPServerStatus(
                        name=server_name,
                        status="online",
                        tool_count=len(server.tools),
                    )
                
                statuses.append(status)
                
            except Exception as e:
                status = MCPServerStatus(
                    name=server_name,
                    status="error",
                    tool_count=len(server.tools),
                    error_message=str(e),
                )
                statuses.append(status)
        
        return statuses
    
    async def reload_server(self, server_name: str) -> bool:
        """
        重新加载服务器
        
        Args:
            server_name: 服务器名称
        
        Returns:
            是否成功
        """
        server = self.servers.get(server_name)
        
        if not server:
            logger.error(f"Server not found: {server_name}")
            return False
        
        try:
            # 断开旧连接
            old_client = self.server_clients.get(server_name)
            if old_client:
                await old_client.disconnect()
            
            # 移除旧工具
            self.tools = {
                k: v for k, v in self.tools.items()
                if v.server_name != server_name
            }
            
            # 重新注册
            await self.register_server(server)
            
            logger.info(f"Server {server_name} reloaded")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reload server {server_name}: {e}")
            return False


# 全局实例
mcp_registry = MCPRegistry()

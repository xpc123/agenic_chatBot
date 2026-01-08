# -*- coding: utf-8 -*-
"""
MCP (Model Context Protocol) 测试

测试 MCP 集成的功能：
- 服务器连接
- 工具发现
- 工具执行
- 资源访问
- 错误处理
"""
import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestMCPClient:
    """测试 MCP 客户端"""
    
    @pytest.fixture
    def mcp_client(self):
        """创建 MCP 客户端"""
        from app.mcp.client import MCPClient
        return MCPClient()
    
    @pytest.mark.asyncio
    async def test_connect_to_server(self, mcp_client):
        """测试连接服务器"""
        # Mock 服务器
        with patch.object(mcp_client, '_connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = True
            
            result = await mcp_client.connect("test-server", {
                "type": "stdio",
                "command": "echo"
            })
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_disconnect_from_server(self, mcp_client):
        """测试断开连接"""
        with patch.object(mcp_client, '_disconnect', new_callable=AsyncMock) as mock_disconnect:
            mock_disconnect.return_value = True
            
            await mcp_client.disconnect("test-server")
            
            mock_disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_servers(self, mcp_client):
        """测试列出服务器"""
        mcp_client._servers = {
            "server1": {"type": "stdio", "status": "connected"},
            "server2": {"type": "sse", "status": "disconnected"},
        }
        
        servers = mcp_client.list_servers()
        
        assert len(servers) == 2


class TestMCPToolDiscovery:
    """测试 MCP 工具发现"""
    
    @pytest.fixture
    def mcp_client(self):
        from app.mcp.client import MCPClient
        return MCPClient()
    
    @pytest.mark.asyncio
    async def test_discover_tools(self, mcp_client):
        """测试发现工具"""
        mock_tools = [
            {
                "name": "read_file",
                "description": "Read a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    }
                }
            },
            {
                "name": "write_file",
                "description": "Write a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"}
                    }
                }
            }
        ]
        
        with patch.object(mcp_client, '_list_tools', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = mock_tools
            
            tools = await mcp_client.list_tools("test-server")
            
            assert len(tools) == 2
            assert tools[0]["name"] == "read_file"
    
    @pytest.mark.asyncio
    async def test_get_tool_schema(self, mcp_client):
        """测试获取工具 schema"""
        mock_schema = {
            "name": "test_tool",
            "description": "Test tool",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "param1": {"type": "string"}
                }
            }
        }
        
        with patch.object(mcp_client, '_get_tool_schema', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_schema
            
            schema = await mcp_client.get_tool_schema("test-server", "test_tool")
            
            assert schema["name"] == "test_tool"


class TestMCPToolExecution:
    """测试 MCP 工具执行"""
    
    @pytest.fixture
    def mcp_client(self):
        from app.mcp.client import MCPClient
        return MCPClient()
    
    @pytest.mark.asyncio
    async def test_execute_tool(self, mcp_client):
        """测试执行工具"""
        mock_result = {
            "content": [{"type": "text", "text": "File content here"}]
        }
        
        with patch.object(mcp_client, '_call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_result
            
            result = await mcp_client.call_tool(
                server_name="test-server",
                tool_name="read_file",
                arguments={"path": "/test/file.txt"}
            )
            
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_execute_tool_with_error(self, mcp_client):
        """测试工具执行错误"""
        with patch.object(mcp_client, '_call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("Tool execution failed")
            
            with pytest.raises(Exception):
                await mcp_client.call_tool(
                    server_name="test-server",
                    tool_name="failing_tool",
                    arguments={}
                )


class TestMCPResource:
    """测试 MCP 资源访问"""
    
    @pytest.fixture
    def mcp_client(self):
        from app.mcp.client import MCPClient
        return MCPClient()
    
    @pytest.mark.asyncio
    async def test_list_resources(self, mcp_client):
        """测试列出资源"""
        mock_resources = [
            {"uri": "file:///path/to/file1.txt", "name": "File 1"},
            {"uri": "file:///path/to/file2.txt", "name": "File 2"},
        ]
        
        with patch.object(mcp_client, '_list_resources', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = mock_resources
            
            resources = await mcp_client.list_resources("test-server")
            
            assert len(resources) == 2
    
    @pytest.mark.asyncio
    async def test_read_resource(self, mcp_client):
        """测试读取资源"""
        mock_content = {
            "contents": [{"uri": "file:///test.txt", "text": "Resource content"}]
        }
        
        with patch.object(mcp_client, '_read_resource', new_callable=AsyncMock) as mock_read:
            mock_read.return_value = mock_content
            
            content = await mcp_client.read_resource(
                server_name="test-server",
                uri="file:///test.txt"
            )
            
            assert content is not None


class TestMCPServerManagement:
    """测试 MCP 服务器管理"""
    
    @pytest.fixture
    def mcp_manager(self):
        from app.mcp.manager import MCPManager
        return MCPManager()
    
    @pytest.mark.asyncio
    async def test_add_server(self, mcp_manager):
        """测试添加服务器"""
        config = {
            "type": "stdio",
            "command": "node",
            "args": ["server.js"],
        }
        
        await mcp_manager.add_server("new-server", config)
        
        servers = mcp_manager.list_servers()
        assert "new-server" in [s["name"] for s in servers]
    
    @pytest.mark.asyncio
    async def test_remove_server(self, mcp_manager):
        """测试移除服务器"""
        await mcp_manager.add_server("to-remove", {"type": "stdio"})
        await mcp_manager.remove_server("to-remove")
        
        servers = mcp_manager.list_servers()
        assert "to-remove" not in [s["name"] for s in servers]
    
    @pytest.mark.asyncio
    async def test_get_server_status(self, mcp_manager):
        """测试获取服务器状态"""
        await mcp_manager.add_server("status-test", {"type": "stdio"})
        
        status = await mcp_manager.get_server_status("status-test")
        
        assert "status" in status


class TestMCPIntegration:
    """测试 MCP 集成到 Orchestrator"""
    
    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP 客户端"""
        mock = AsyncMock()
        mock.list_tools.return_value = [
            {"name": "mcp_tool", "description": "MCP Tool"}
        ]
        mock.call_tool.return_value = {"result": "success"}
        return mock
    
    @pytest.mark.asyncio
    async def test_orchestrator_with_mcp_tools(self, mock_mcp_client):
        """测试 Orchestrator 使用 MCP 工具"""
        from app.core.cursor_style_orchestrator import CursorStyleOrchestrator
        
        mock_llm = AsyncMock()
        mock_llm.chat_completion = AsyncMock(return_value="回复")
        
        orchestrator = CursorStyleOrchestrator(
            llm_client=mock_llm,
            tools=[],
            enable_mcp=True,
        )
        
        # 注入 mock MCP 客户端
        orchestrator._mcp_client = mock_mcp_client
        
        # 应该能获取 MCP 工具
        # 具体实现取决于代码结构


class TestMCPErrorHandling:
    """测试 MCP 错误处理"""
    
    @pytest.fixture
    def mcp_client(self):
        from app.mcp.client import MCPClient
        return MCPClient()
    
    @pytest.mark.asyncio
    async def test_connection_timeout(self, mcp_client):
        """测试连接超时"""
        with patch.object(mcp_client, '_connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(asyncio.TimeoutError):
                await mcp_client.connect("slow-server", {"type": "stdio"})
    
    @pytest.mark.asyncio
    async def test_invalid_server_config(self, mcp_client):
        """测试无效服务器配置"""
        with pytest.raises(Exception):
            await mcp_client.connect("invalid", {})
    
    @pytest.mark.asyncio
    async def test_tool_not_found(self, mcp_client):
        """测试工具不存在"""
        with patch.object(mcp_client, '_call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("Tool not found")
            
            with pytest.raises(Exception):
                await mcp_client.call_tool(
                    server_name="test-server",
                    tool_name="nonexistent_tool",
                    arguments={}
                )


class TestMCPConfiguration:
    """测试 MCP 配置"""
    
    def test_load_config(self, tmp_path):
        """测试加载配置"""
        from app.mcp.config import MCPConfig
        import json
        
        config_data = {
            "servers": {
                "test-server": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["server.js"]
                }
            }
        }
        
        config_file = tmp_path / "mcp_config.json"
        config_file.write_text(json.dumps(config_data))
        
        config = MCPConfig.load(str(config_file))
        
        assert "test-server" in config.servers
    
    def test_save_config(self, tmp_path):
        """测试保存配置"""
        from app.mcp.config import MCPConfig
        
        config = MCPConfig()
        config.add_server("new-server", {
            "type": "sse",
            "url": "http://localhost:3000"
        })
        
        config_file = tmp_path / "mcp_config.json"
        config.save(str(config_file))
        
        assert config_file.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


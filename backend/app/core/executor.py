"""
工具执行器 - Tool Executor
负责执行MCP工具调用
"""
from typing import Dict, Any, Optional
from loguru import logger
import asyncio
from datetime import datetime

from ..models.tool import ToolCall, ToolResult
from ..config import settings


class ToolExecutor:
    """
    工具执行器
    
    职责:
    1. 执行工具调用
    2. 处理工具超时
    3. 错误处理和重试
    4. 执行结果缓存
    """
    
    def __init__(self, mcp_registry):
        """
        Args:
            mcp_registry: MCP工具注册中心
        """
        self.registry = mcp_registry
        self.timeout = settings.MCP_TIMEOUT
        self.max_retries = settings.MCP_MAX_RETRIES
        
        # 执行结果缓存 (可选)
        self.result_cache: Dict[str, ToolResult] = {}
        
        logger.info("ToolExecutor initialized")
    
    async def execute_tool(
        self,
        tool_call: Dict[str, Any],
        retry_count: int = 0,
    ) -> ToolResult:
        """
        执行工具调用
        
        Args:
            tool_call: 工具调用信息
                {
                    "name": "tool_name",
                    "arguments": {"arg1": "value1"}
                }
            retry_count: 重试次数
        
        Returns:
            工具执行结果
        """
        tool_name = tool_call.get("name")
        arguments = tool_call.get("arguments", {})
        
        logger.info(f"Executing tool: {tool_name}")
        
        start_time = datetime.now()
        
        try:
            # 从注册中心获取工具
            tool = self.registry.get_tool(tool_name)
            
            if not tool:
                raise ValueError(f"Tool not found: {tool_name}")
            
            # 执行工具 (带超时)
            result = await asyncio.wait_for(
                self._call_tool(tool, arguments),
                timeout=self.timeout,
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            tool_result = ToolResult(
                tool_call_id=self._generate_call_id(tool_call),
                success=True,
                result=result,
                execution_time=execution_time,
            )
            
            logger.info(f"Tool {tool_name} executed successfully in {execution_time:.2f}s")
            return tool_result
            
        except asyncio.TimeoutError:
            logger.error(f"Tool {tool_name} timed out after {self.timeout}s")
            
            # 重试
            if retry_count < self.max_retries:
                logger.info(f"Retrying tool {tool_name} (attempt {retry_count + 1})")
                return await self.execute_tool(tool_call, retry_count + 1)
            
            return ToolResult(
                tool_call_id=self._generate_call_id(tool_call),
                success=False,
                result=None,
                error=f"Tool execution timed out after {self.timeout}s",
                execution_time=self.timeout,
            )
            
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ToolResult(
                tool_call_id=self._generate_call_id(tool_call),
                success=False,
                result=None,
                error=str(e),
                execution_time=execution_time,
            )
    
    async def _call_tool(
        self,
        tool: Dict[str, Any],
        arguments: Dict[str, Any],
    ) -> Any:
        """
        实际调用工具
        
        通过MCP协议与工具服务器通信
        """
        server_name = tool.get("server_name")
        tool_name = tool.get("name")
        
        # 获取MCP服务器客户端
        mcp_client = self.registry.get_server_client(server_name)
        
        if not mcp_client:
            raise ValueError(f"MCP server not found: {server_name}")
        
        # 调用工具
        result = await mcp_client.call_tool(tool_name, arguments)
        
        return result
    
    def _generate_call_id(self, tool_call: Dict[str, Any]) -> str:
        """生成工具调用ID"""
        import hashlib
        import json
        
        call_str = json.dumps(tool_call, sort_keys=True)
        return hashlib.md5(call_str.encode()).hexdigest()[:16]
    
    async def execute_parallel(
        self,
        tool_calls: list[Dict[str, Any]],
    ) -> list[ToolResult]:
        """
        并行执行多个工具
        
        Args:
            tool_calls: 工具调用列表
        
        Returns:
            执行结果列表
        """
        logger.info(f"Executing {len(tool_calls)} tools in parallel")
        
        tasks = [
            self.execute_tool(tool_call)
            for tool_call in tool_calls
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    ToolResult(
                        tool_call_id=self._generate_call_id(tool_calls[i]),
                        success=False,
                        result=None,
                        error=str(result),
                        execution_time=0,
                    )
                )
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_langchain_tools(self) -> list:
        """
        获取 LangChain 兼容的工具列表
        
        将 MCP 工具转换为 LangChain @tool 装饰器格式
        
        Returns:
            LangChain 工具列表
        """
        from langchain.tools import tool
        
        langchain_tools = []
        
        try:
            # 获取所有注册的 MCP 工具
            mcp_tools = self.registry.list_all_tools()
            
            for mcp_tool in mcp_tools:
                tool_name = mcp_tool.get("name")
                tool_desc = mcp_tool.get("description", "")
                
                # 动态创建 LangChain 工具
                # 注意：这里使用闭包来捕获工具信息
                def create_tool(name: str, description: str):
                    @tool
                    async def dynamic_tool(**kwargs) -> str:
                        f"""
                        {description}
                        """
                        result = await self.execute_tool({
                            "name": name,
                            "arguments": kwargs
                        })
                        
                        if result.success:
                            return str(result.result)
                        else:
                            return f"工具执行失败: {result.error}"
                    
                    dynamic_tool.__name__ = name
                    dynamic_tool.__doc__ = description
                    return dynamic_tool
                
                langchain_tools.append(create_tool(tool_name, tool_desc))
        
        except Exception as e:
            logger.warning(f"Failed to get LangChain tools: {e}")
        
        return langchain_tools

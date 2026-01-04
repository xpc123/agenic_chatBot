# -*- coding: utf-8 -*-
"""
工具执行器 - Tool Executor
负责执行MCP工具调用

支持多种工具调用格式:
- OpenAI: {"name": "...", "arguments": {...}}
- OpenAI Function: {"function": {"name": "...", "arguments": {...}}}
- Anthropic: {"name": "...", "input": {...}}
- LangChain: {"name": "...", "args": {...}}
- 标准化格式: {"name": "...", "arguments": {...}}
"""
from typing import Dict, Any, Optional, Union, List
from loguru import logger
import asyncio
import json
import re
from datetime import datetime

from ..models.tool import ToolCall, ToolResult
from ..config import settings


# ==================== 工具调用解析器 ====================

class ToolCallParser:
    """
    统一工具调用解析器
    
    支持多种LLM提供商的工具调用格式，将其标准化为:
    {
        "id": str,           # 工具调用ID（可选）
        "name": str,         # 工具名称
        "arguments": dict    # 工具参数
    }
    """
    
    # 已知的参数字段名（按优先级排序）
    ARGUMENT_FIELDS = ["arguments", "args", "input", "parameters", "params"]
    
    @classmethod
    def parse(cls, tool_call: Union[Dict[str, Any], str]) -> Dict[str, Any]:
        """
        解析工具调用，返回标准化格式
        
        Args:
            tool_call: 工具调用数据（字典或JSON字符串）
        
        Returns:
            标准化的工具调用字典
        
        Raises:
            ValueError: 无法解析工具调用格式
        """
        # 如果是字符串，尝试解析为JSON
        if isinstance(tool_call, str):
            tool_call = cls._parse_json_string(tool_call)
        
        if not isinstance(tool_call, dict):
            raise ValueError(f"工具调用必须是字典类型，收到: {type(tool_call)}")
        
        # 处理 OpenAI Function 格式: {"function": {"name": "...", "arguments": ...}}
        if "function" in tool_call and isinstance(tool_call["function"], dict):
            inner = tool_call["function"]
            return cls._normalize({
                "id": tool_call.get("id", ""),
                "name": inner.get("name", ""),
                "arguments": cls._extract_arguments(inner),
            })
        
        # 处理标准格式: {"name": "...", "arguments|args|input": ...}
        if "name" in tool_call:
            return cls._normalize({
                "id": tool_call.get("id", tool_call.get("tool_call_id", "")),
                "name": tool_call["name"],
                "arguments": cls._extract_arguments(tool_call),
            })
        
        # 处理可能的嵌套格式: {"tool": {"name": "...", ...}}
        if "tool" in tool_call and isinstance(tool_call["tool"], dict):
            return cls.parse(tool_call["tool"])
        
        # 处理 Anthropic 风格: {"type": "tool_use", "name": "...", "input": ...}
        if tool_call.get("type") == "tool_use":
            return cls._normalize({
                "id": tool_call.get("id", ""),
                "name": tool_call.get("name", ""),
                "arguments": tool_call.get("input", {}),
            })
        
        raise ValueError(f"无法解析工具调用格式: {tool_call}")
    
    @classmethod
    def parse_batch(cls, tool_calls: List[Any]) -> List[Dict[str, Any]]:
        """
        批量解析工具调用
        
        Args:
            tool_calls: 工具调用列表
        
        Returns:
            标准化的工具调用列表（跳过解析失败的项）
        """
        results = []
        for tc in tool_calls:
            try:
                results.append(cls.parse(tc))
            except ValueError as e:
                logger.warning(f"跳过无法解析的工具调用: {e}")
        return results
    
    @classmethod
    def _parse_json_string(cls, s: str) -> Dict[str, Any]:
        """解析JSON字符串，支持多种格式"""
        s = s.strip()
        
        # 尝试直接解析
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
        
        # 尝试从Markdown代码块中提取
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', s, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 尝试提取第一个JSON对象
        brace_match = re.search(r'\{[^{}]*\}', s, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except json.JSONDecodeError:
                pass
        
        raise ValueError(f"无法从字符串解析JSON: {s[:100]}...")
    
    @classmethod
    def _extract_arguments(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """从数据中提取参数"""
        for field in cls.ARGUMENT_FIELDS:
            if field in data:
                args = data[field]
                # 如果参数是字符串，尝试解析为JSON
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        # 保持为字符串
                        pass
                return args if isinstance(args, dict) else {}
        return {}
    
    @classmethod
    def _normalize(cls, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """标准化解析结果"""
        return {
            "id": str(parsed.get("id", "")) or "",
            "name": str(parsed.get("name", "")).strip(),
            "arguments": parsed.get("arguments", {}),
        }
    
    @classmethod
    def extract_from_llm_response(cls, response: str) -> List[Dict[str, Any]]:
        """
        从LLM文本响应中提取工具调用
        
        支持多种格式:
        - JSON代码块
        - Action/Action Input格式
        - 函数调用格式
        
        Args:
            response: LLM响应文本
        
        Returns:
            提取的工具调用列表
        """
        tool_calls = []
        
        # 1. 尝试提取JSON代码块中的工具调用
        json_blocks = re.findall(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        for block in json_blocks:
            try:
                data = json.loads(block)
                if "name" in data or "function" in data or "tool" in data:
                    tool_calls.append(cls.parse(data))
            except (json.JSONDecodeError, ValueError):
                continue
        
        # 2. 尝试提取 Action/Action Input 格式 (ReAct风格)
        action_pattern = r'Action:\s*(\w+)\s*\nAction Input:\s*(\{.*?\}|\S+)'
        for match in re.finditer(action_pattern, response, re.DOTALL):
            action_name = match.group(1)
            action_input = match.group(2).strip()
            
            try:
                if action_input.startswith('{'):
                    args = json.loads(action_input)
                else:
                    args = {"input": action_input}
                
                tool_calls.append({
                    "id": "",
                    "name": action_name,
                    "arguments": args,
                })
            except json.JSONDecodeError:
                tool_calls.append({
                    "id": "",
                    "name": action_name,
                    "arguments": {"input": action_input},
                })
        
        # 3. 尝试提取函数调用格式: tool_name(arg1, arg2)
        func_pattern = r'(\w+)\s*\(\s*(\{.*?\})\s*\)'
        for match in re.finditer(func_pattern, response, re.DOTALL):
            func_name = match.group(1)
            func_args = match.group(2)
            
            # 排除常见的非工具调用
            if func_name.lower() in ['print', 'log', 'console', 'return', 'if', 'for', 'while']:
                continue
            
            try:
                args = json.loads(func_args)
                tool_calls.append({
                    "id": "",
                    "name": func_name,
                    "arguments": args,
                })
            except json.JSONDecodeError:
                continue
        
        return tool_calls


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
        tool_call: Union[Dict[str, Any], str],
        retry_count: int = 0,
    ) -> ToolResult:
        """
        执行工具调用
        
        支持多种工具调用格式:
        - OpenAI: {"name": "...", "arguments": {...}}
        - OpenAI Function: {"function": {"name": "...", "arguments": {...}}}
        - Anthropic: {"name": "...", "input": {...}}
        - LangChain: {"name": "...", "args": {...}}
        
        Args:
            tool_call: 工具调用信息（支持多种格式）
            retry_count: 重试次数
        
        Returns:
            工具执行结果
        """
        # 使用统一解析器标准化工具调用格式
        try:
            parsed_call = ToolCallParser.parse(tool_call)
        except ValueError as e:
            logger.error(f"Failed to parse tool call: {e}")
            return ToolResult(
                tool_call_id="parse_error",
                success=False,
                result=None,
                error=f"工具调用解析失败: {e}",
                execution_time=0,
            )
        
        tool_name = parsed_call["name"]
        arguments = parsed_call["arguments"]
        tool_call_id = parsed_call.get("id", "")
        
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
                tool_call_id=tool_call_id or self._generate_call_id(parsed_call),
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
                return await self.execute_tool(parsed_call, retry_count + 1)
            
            return ToolResult(
                tool_call_id=tool_call_id or self._generate_call_id(parsed_call),
                success=False,
                result=None,
                error=f"Tool execution timed out after {self.timeout}s",
                execution_time=self.timeout,
            )
            
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ToolResult(
                tool_call_id=tool_call_id or self._generate_call_id(parsed_call),
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
            mcp_tools = self.registry.list_tools()
            
            for mcp_tool in mcp_tools:
                tool_name = mcp_tool.name
                tool_desc = mcp_tool.description
                
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


# ==================== 导出 ====================

__all__ = [
    "ToolCallParser",
    "ToolExecutor",
]

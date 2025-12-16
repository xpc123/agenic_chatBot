# -*- coding: utf-8 -*-
"""
动态工具注册系统

支持:
- 运行时动态注册/注销工具
- 工具热加载
- 工具权限管理
- 外部 API 工具配置化创建
- 工具执行统计

使用示例:
    registry = ToolRegistry()
    registry.register(my_tool)
    registry.register_from_config(api_config)
    tools = registry.get_tools(user_permissions=['basic', 'api'])
"""
from typing import Optional, List, Dict, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import asyncio
import httpx
from loguru import logger
from langchain.tools import tool
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


# ==================== 数据模型 ====================

class ToolPermission(str, Enum):
    """工具权限级别"""
    PUBLIC = "public"           # 所有用户可用
    BASIC = "basic"             # 基础用户
    ADVANCED = "advanced"       # 高级用户
    ADMIN = "admin"             # 管理员
    DANGEROUS = "dangerous"     # 危险操作，需要确认


@dataclass
class ToolMetadata:
    """工具元数据"""
    name: str
    description: str
    permission: ToolPermission = ToolPermission.PUBLIC
    category: str = "general"
    version: str = "1.0.0"
    author: str = "system"
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    
    # 执行统计
    call_count: int = 0
    success_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0


@dataclass
class APIToolConfig:
    """外部 API 工具配置"""
    name: str
    description: str
    url: str
    method: str = "POST"
    headers: Dict[str, str] = field(default_factory=dict)
    body_template: Dict[str, Any] = field(default_factory=dict)
    response_path: str = ""  # JSONPath 到响应数据
    timeout: float = 30.0
    permission: ToolPermission = ToolPermission.BASIC
    category: str = "api"
    
    # 参数定义
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    # 示例: [{"name": "query", "type": "string", "description": "搜索查询", "required": True}]


# ==================== 工具注册表 ====================

class ToolRegistry:
    """
    动态工具注册表
    
    管理所有工具的注册、查询、执行和统计
    """
    
    def __init__(self):
        self._tools: Dict[str, Any] = {}
        self._metadata: Dict[str, ToolMetadata] = {}
        self._api_configs: Dict[str, APIToolConfig] = {}
        self._http_client: Optional[httpx.AsyncClient] = None
        
    async def _get_http_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端（懒加载）"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    async def close(self):
        """关闭资源"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    # ==================== 注册方法 ====================
    
    def register(
        self,
        tool_instance: Any,
        permission: ToolPermission = ToolPermission.PUBLIC,
        category: str = "general",
        enabled: bool = True,
    ) -> bool:
        """
        注册一个工具
        
        Args:
            tool_instance: LangChain 工具实例
            permission: 权限级别
            category: 工具分类
            enabled: 是否启用
        
        Returns:
            是否注册成功
        """
        try:
            name = tool_instance.name
            
            if name in self._tools:
                logger.warning(f"工具 '{name}' 已存在，将被覆盖")
            
            self._tools[name] = tool_instance
            self._metadata[name] = ToolMetadata(
                name=name,
                description=tool_instance.description or "",
                permission=permission,
                category=category,
                enabled=enabled,
            )
            
            logger.info(f"✅ 注册工具: {name} (权限: {permission.value}, 分类: {category})")
            return True
            
        except Exception as e:
            logger.error(f"❌ 注册工具失败: {e}")
            return False
    
    def register_many(
        self,
        tools: List[Any],
        permission: ToolPermission = ToolPermission.PUBLIC,
        category: str = "general",
    ) -> int:
        """
        批量注册工具
        
        Returns:
            成功注册的数量
        """
        count = 0
        for t in tools:
            if self.register(t, permission, category):
                count += 1
        return count
    
    def unregister(self, name: str) -> bool:
        """
        注销一个工具
        
        Args:
            name: 工具名称
        
        Returns:
            是否注销成功
        """
        if name in self._tools:
            del self._tools[name]
            del self._metadata[name]
            self._api_configs.pop(name, None)
            logger.info(f"🗑️ 注销工具: {name}")
            return True
        return False
    
    def enable(self, name: str) -> bool:
        """启用工具"""
        if name in self._metadata:
            self._metadata[name].enabled = True
            logger.info(f"✅ 启用工具: {name}")
            return True
        return False
    
    def disable(self, name: str) -> bool:
        """禁用工具"""
        if name in self._metadata:
            self._metadata[name].enabled = False
            logger.info(f"⏸️ 禁用工具: {name}")
            return True
        return False
    
    # ==================== API 工具创建 ====================
    
    def register_api_tool(self, config: APIToolConfig) -> bool:
        """
        从配置创建并注册 API 工具
        
        Args:
            config: API 工具配置
        
        Returns:
            是否成功
        """
        try:
            # 动态创建工具函数
            tool_func = self._create_api_tool_function(config)
            
            # 创建 StructuredTool
            from langchain_core.tools import StructuredTool
            
            # 构建参数 schema
            param_schema = self._build_param_schema(config.parameters)
            
            structured_tool = StructuredTool.from_function(
                func=tool_func,
                name=config.name,
                description=config.description,
                args_schema=param_schema,
                coroutine=self._create_async_api_tool_function(config),
            )
            
            # 注册
            self._api_configs[config.name] = config
            return self.register(
                structured_tool,
                permission=config.permission,
                category=config.category,
            )
            
        except Exception as e:
            logger.error(f"❌ 创建 API 工具失败: {e}")
            return False
    
    def _create_api_tool_function(self, config: APIToolConfig) -> Callable:
        """创建同步 API 调用函数"""
        def api_call(**kwargs) -> str:
            import httpx
            try:
                # 构建请求体
                body = self._build_request_body(config.body_template, kwargs)
                
                # 发送请求
                with httpx.Client(timeout=config.timeout) as client:
                    if config.method.upper() == "GET":
                        response = client.get(config.url, params=kwargs, headers=config.headers)
                    else:
                        response = client.request(
                            method=config.method.upper(),
                            url=config.url,
                            json=body,
                            headers=config.headers,
                        )
                
                response.raise_for_status()
                result = response.json()
                
                # 提取响应数据
                if config.response_path:
                    result = self._extract_json_path(result, config.response_path)
                
                return f"✅ API 调用成功:\n{json.dumps(result, ensure_ascii=False, indent=2)}"
                
            except httpx.TimeoutException:
                return f"❌ API 超时: {config.url}"
            except httpx.HTTPStatusError as e:
                return f"❌ HTTP 错误 {e.response.status_code}: {e.response.text}"
            except Exception as e:
                return f"❌ API 调用失败: {str(e)}"
        
        return api_call
    
    def _create_async_api_tool_function(self, config: APIToolConfig) -> Callable:
        """创建异步 API 调用函数"""
        async def async_api_call(**kwargs) -> str:
            try:
                client = await self._get_http_client()
                
                # 构建请求体
                body = self._build_request_body(config.body_template, kwargs)
                
                # 发送请求
                if config.method.upper() == "GET":
                    response = await client.get(config.url, params=kwargs, headers=config.headers)
                else:
                    response = await client.request(
                        method=config.method.upper(),
                        url=config.url,
                        json=body,
                        headers=config.headers,
                        timeout=config.timeout,
                    )
                
                response.raise_for_status()
                result = response.json()
                
                # 提取响应数据
                if config.response_path:
                    result = self._extract_json_path(result, config.response_path)
                
                return f"✅ API 调用成功:\n{json.dumps(result, ensure_ascii=False, indent=2)}"
                
            except httpx.TimeoutException:
                return f"❌ API 超时: {config.url}"
            except httpx.HTTPStatusError as e:
                return f"❌ HTTP 错误 {e.response.status_code}: {e.response.text}"
            except Exception as e:
                return f"❌ API 调用失败: {str(e)}"
        
        return async_api_call
    
    def _build_request_body(self, template: Dict, params: Dict) -> Dict:
        """构建请求体，替换模板变量"""
        import re
        
        def replace_vars(obj, params):
            if isinstance(obj, str):
                # 替换 {{var}} 格式的变量
                for key, value in params.items():
                    obj = obj.replace(f"{{{{{key}}}}}", str(value))
                return obj
            elif isinstance(obj, dict):
                return {k: replace_vars(v, params) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_vars(item, params) for item in obj]
            return obj
        
        if template:
            return replace_vars(template, params)
        return params
    
    def _extract_json_path(self, data: Any, path: str) -> Any:
        """从 JSON 数据中提取指定路径的值"""
        if not path:
            return data
        
        parts = path.split('.')
        result = data
        for part in parts:
            if isinstance(result, dict):
                result = result.get(part)
            elif isinstance(result, list) and part.isdigit():
                result = result[int(part)]
            else:
                return data
        return result
    
    def _build_param_schema(self, parameters: List[Dict]) -> Any:
        """构建 Pydantic 参数 schema"""
        from pydantic import create_model
        
        if not parameters:
            return None
        
        fields = {}
        for param in parameters:
            name = param["name"]
            param_type = param.get("type", "string")
            description = param.get("description", "")
            required = param.get("required", True)
            default = param.get("default", ...)
            
            # 类型映射
            type_map = {
                "string": str,
                "integer": int,
                "number": float,
                "boolean": bool,
            }
            
            python_type = type_map.get(param_type, str)
            
            if required:
                fields[name] = (python_type, Field(description=description))
            else:
                fields[name] = (Optional[python_type], Field(default=default, description=description))
        
        return create_model("APIParams", **fields)
    
    # ==================== 从配置文件加载 ====================
    
    def load_from_config(self, config_path: str) -> int:
        """
        从配置文件加载 API 工具
        
        Args:
            config_path: 配置文件路径 (JSON)
        
        Returns:
            加载的工具数量
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            count = 0
            for tool_config in config.get("api_tools", []):
                api_config = APIToolConfig(
                    name=tool_config["name"],
                    description=tool_config["description"],
                    url=tool_config["url"],
                    method=tool_config.get("method", "POST"),
                    headers=tool_config.get("headers", {}),
                    body_template=tool_config.get("body_template", {}),
                    response_path=tool_config.get("response_path", ""),
                    timeout=tool_config.get("timeout", 30.0),
                    permission=ToolPermission(tool_config.get("permission", "basic")),
                    category=tool_config.get("category", "api"),
                    parameters=tool_config.get("parameters", []),
                )
                
                if self.register_api_tool(api_config):
                    count += 1
            
            logger.info(f"📦 从配置加载了 {count} 个 API 工具")
            return count
            
        except Exception as e:
            logger.error(f"❌ 加载配置文件失败: {e}")
            return 0
    
    # ==================== 查询方法 ====================
    
    def get_tool(self, name: str) -> Optional[Any]:
        """获取指定工具"""
        meta = self._metadata.get(name)
        if meta and meta.enabled:
            return self._tools.get(name)
        return None
    
    def get_tools(
        self,
        permissions: Optional[Set[ToolPermission]] = None,
        categories: Optional[Set[str]] = None,
        enabled_only: bool = True,
    ) -> List[Any]:
        """
        获取工具列表
        
        Args:
            permissions: 允许的权限级别集合
            categories: 允许的分类集合
            enabled_only: 是否只返回启用的工具
        
        Returns:
            符合条件的工具列表
        """
        result = []
        
        for name, tool_instance in self._tools.items():
            meta = self._metadata.get(name)
            if not meta:
                continue
            
            # 检查启用状态
            if enabled_only and not meta.enabled:
                continue
            
            # 检查权限
            if permissions and meta.permission not in permissions:
                continue
            
            # 检查分类
            if categories and meta.category not in categories:
                continue
            
            result.append(tool_instance)
        
        return result
    
    def get_all_tools(self) -> List[Any]:
        """获取所有启用的工具"""
        return self.get_tools(enabled_only=True)
    
    def get_tool_names(self) -> List[str]:
        """获取所有工具名称"""
        return list(self._tools.keys())
    
    def get_metadata(self, name: str) -> Optional[ToolMetadata]:
        """获取工具元数据"""
        return self._metadata.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有工具信息"""
        result = []
        for name, meta in self._metadata.items():
            result.append({
                "name": name,
                "description": meta.description,
                "permission": meta.permission.value,
                "category": meta.category,
                "enabled": meta.enabled,
                "call_count": meta.call_count,
            })
        return result
    
    # ==================== 统计方法 ====================
    
    def record_call(self, name: str, success: bool, latency_ms: float):
        """记录工具调用统计"""
        meta = self._metadata.get(name)
        if meta:
            meta.call_count += 1
            if success:
                meta.success_count += 1
            else:
                meta.error_count += 1
            
            # 更新平均延迟
            old_avg = meta.avg_latency_ms
            count = meta.call_count
            meta.avg_latency_ms = old_avg + (latency_ms - old_avg) / count
    
    def get_stats(self) -> Dict[str, Any]:
        """获取工具统计信息"""
        total_calls = sum(m.call_count for m in self._metadata.values())
        total_success = sum(m.success_count for m in self._metadata.values())
        total_errors = sum(m.error_count for m in self._metadata.values())
        
        return {
            "total_tools": len(self._tools),
            "enabled_tools": sum(1 for m in self._metadata.values() if m.enabled),
            "total_calls": total_calls,
            "success_rate": total_success / total_calls if total_calls > 0 else 0,
            "error_count": total_errors,
            "by_category": self._get_stats_by_category(),
        }
    
    def _get_stats_by_category(self) -> Dict[str, int]:
        """按分类统计工具数量"""
        stats = {}
        for meta in self._metadata.values():
            category = meta.category
            stats[category] = stats.get(category, 0) + 1
        return stats


# ==================== 全局实例 ====================

_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """获取全局工具注册表"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def init_default_tools():
    """初始化默认工具"""
    from backend.app.core.tools import get_builtin_tools
    
    registry = get_tool_registry()
    
    # 注册内置工具
    builtin_tools = get_builtin_tools()
    registry.register_many(builtin_tools, permission=ToolPermission.PUBLIC, category="builtin")
    
    logger.info(f"✅ 初始化了 {len(builtin_tools)} 个默认工具")
    return registry

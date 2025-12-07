"""
自定义异常类 - 提供统一的错误处理
"""
from typing import Optional, Dict, Any


class ChatBotException(Exception):
    """基础异常类"""
    
    def __init__(
        self,
        message: str,
        code: str = "CHATBOT_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "type": self.__class__.__name__,
                "details": self.details
            }
        }


class AgentExecutionError(ChatBotException):
    """Agent 执行错误"""
    
    def __init__(self, message: str, iteration: int = 0, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="AGENT_EXECUTION_ERROR",
            details={**(details or {}), "iteration": iteration}
        )
        self.iteration = iteration


class ToolExecutionError(ChatBotException):
    """工具执行错误"""
    
    def __init__(self, tool_name: str, error: str, details: Optional[Dict] = None):
        super().__init__(
            message=f"Tool '{tool_name}' execution failed: {error}",
            code="TOOL_EXECUTION_ERROR",
            details={**(details or {}), "tool_name": tool_name, "error": error}
        )
        self.tool_name = tool_name


class RAGRetrievalError(ChatBotException):
    """RAG 检索错误"""
    
    def __init__(self, message: str, query: str = "", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="RAG_RETRIEVAL_ERROR",
            details={**(details or {}), "query": query}
        )
        self.query = query


class MCPConnectionError(ChatBotException):
    """MCP 服务器连接错误"""
    
    def __init__(self, server_url: str, error: str, details: Optional[Dict] = None):
        super().__init__(
            message=f"Failed to connect to MCP server '{server_url}': {error}",
            code="MCP_CONNECTION_ERROR",
            details={**(details or {}), "server_url": server_url, "error": error}
        )
        self.server_url = server_url


class ContextLoadError(ChatBotException):
    """上下文加载错误"""
    
    def __init__(self, path: str, error: str, details: Optional[Dict] = None):
        super().__init__(
            message=f"Failed to load context from '{path}': {error}",
            code="CONTEXT_LOAD_ERROR",
            details={**(details or {}), "path": path, "error": error}
        )
        self.path = path


class SecurityError(ChatBotException):
    """安全错误"""
    
    def __init__(
        self,
        message: str,
        violation_type: str = "UNKNOWN",
        details: Optional[Dict] = None
    ):
        super().__init__(
            message=message,
            code="SECURITY_ERROR",
            details={**(details or {}), "violation_type": violation_type}
        )
        self.violation_type = violation_type


class ValidationError(ChatBotException):
    """输入验证错误"""
    
    def __init__(self, field: str, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=f"Validation error for '{field}': {message}",
            code="VALIDATION_ERROR",
            details={**(details or {}), "field": field}
        )
        self.field = field


class RateLimitExceeded(ChatBotException):
    """速率限制错误"""
    
    def __init__(self, limit: str, retry_after: int = 60, details: Optional[Dict] = None):
        super().__init__(
            message=f"Rate limit exceeded: {limit}. Retry after {retry_after}s",
            code="RATE_LIMIT_EXCEEDED",
            details={**(details or {}), "retry_after": retry_after, "limit": limit}
        )
        self.retry_after = retry_after


class ConfigurationError(ChatBotException):
    """配置错误"""
    
    def __init__(self, message: str, config_key: str = "", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            details={**(details or {}), "config_key": config_key}
        )
        self.config_key = config_key


class LLMError(ChatBotException):
    """LLM 调用错误"""
    
    def __init__(
        self,
        message: str,
        provider: str = "",
        model: str = "",
        details: Optional[Dict] = None
    ):
        super().__init__(
            message=message,
            code="LLM_ERROR",
            details={**(details or {}), "provider": provider, "model": model}
        )
        self.provider = provider
        self.model = model

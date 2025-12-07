"""
Universal Agentic ChatBot - Python SDK

提供Python客户端库，方便B端产品集成
"""
from typing import Dict, Any, Optional, List, Iterator
import requests
import hmac
import hashlib
import time
import json
from dataclasses import dataclass
from enum import Enum


class EventType(Enum):
    """事件类型"""
    THOUGHT = "thought"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    TEXT = "text"
    CONTEXT = "context"
    SOURCES = "sources"
    ERROR = "error"


@dataclass
class ChatBotConfig:
    """ChatBot配置"""
    app_id: str
    app_secret: str
    base_url: str = "http://localhost:8000"
    workspace_root: Optional[str] = None
    mcp_servers: Optional[List[Dict[str, Any]]] = None
    rag_config: Optional[Dict[str, Any]] = None
    webhook_url: Optional[str] = None
    timeout: int = 30


class ChatBotSDK:
    """
    Universal Agentic ChatBot SDK
    
    用法:
        >>> sdk = ChatBotSDK(config)
        >>> sdk.initialize()
        >>> response = sdk.chat("你好")
        >>> print(response)
    """
    
    def __init__(self, config: ChatBotConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })
        self._initialized = False
    
    def _generate_signature(self, timestamp: int, body: str = "") -> str:
        """生成HMAC-SHA256签名"""
        message = f"{self.config.app_id}{timestamp}{body}"
        return hmac.new(
            self.config.app_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def _get_headers(self, body: str = "") -> Dict[str, str]:
        """获取请求头（包含认证信息）"""
        timestamp = int(time.time())
        return {
            "X-App-Id": self.config.app_id,
            "X-Timestamp": str(timestamp),
            "X-Signature": self._generate_signature(timestamp, body),
        }
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        stream: bool = False
    ) -> requests.Response:
        """发送HTTP请求"""
        url = f"{self.config.base_url}{endpoint}"
        body = json.dumps(data) if data else ""
        headers = self._get_headers(body)
        
        response = self.session.request(
            method=method,
            url=url,
            data=body if body else None,
            headers=headers,
            timeout=self.config.timeout,
            stream=stream
        )
        
        response.raise_for_status()
        return response
    
    def initialize(self) -> Dict[str, Any]:
        """
        初始化集成
        
        Returns:
            初始化结果
        """
        config_data = {
            "app_id": self.config.app_id,
            "app_secret": self.config.app_secret,
        }
        
        if self.config.workspace_root:
            config_data["workspace_root"] = self.config.workspace_root
        
        if self.config.mcp_servers:
            config_data["mcp_servers"] = self.config.mcp_servers
        
        if self.config.rag_config:
            config_data["rag_config"] = self.config.rag_config
        
        if self.config.webhook_url:
            config_data["webhook_url"] = self.config.webhook_url
        
        response = self._request("POST", "/api/v1/sdk/init", data=config_data)
        result = response.json()
        
        self._initialized = True
        return result
    
    def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        stream: bool = False,
        use_rag: bool = True,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        发送聊天消息
        
        Args:
            message: 用户消息（支持@路径引用）
            session_id: 会话ID（可选）
            stream: 是否流式输出
            use_rag: 是否使用RAG检索
            context: 额外上下文
        
        Returns:
            如果stream=False，返回完整响应字典
            如果stream=True，返回Iterator[Dict]
        """
        if not self._initialized:
            raise RuntimeError("SDK未初始化，请先调用initialize()")
        
        payload = {
            "message": message,
            "session_id": session_id,
            "stream": stream,
            "use_rag": use_rag,
        }
        
        if context:
            payload["context"] = context
        
        if stream:
            return self._stream_chat(payload)
        else:
            response = self._request("POST", "/api/v1/sdk/chat", data=payload)
            return response.json()
    
    def _stream_chat(self, payload: Dict) -> Iterator[Dict[str, Any]]:
        """流式聊天"""
        response = self._request(
            "POST",
            "/api/v1/sdk/chat",
            data=payload,
            stream=True
        )
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]  # 去掉 'data: ' 前缀
                    if data.strip() == '[DONE]':
                        break
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        continue
    
    def upload_document(
        self,
        content: str,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        上传文档到RAG知识库
        
        Args:
            content: 文档内容
            filename: 文件名
            metadata: 文档元数据
        
        Returns:
            上传结果
        """
        payload = {
            "content": content,
            "filename": filename,
            "metadata": metadata or {}
        }
        
        response = self._request("POST", "/api/v1/sdk/upload", data=payload)
        return response.json()
    
    def upload_file(
        self,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        从文件路径上传文档
        
        Args:
            file_path: 文件路径
            metadata: 文档元数据
        
        Returns:
            上传结果
        """
        import os
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        filename = os.path.basename(file_path)
        return self.upload_document(content, filename, metadata)
    
    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        endpoint: str,
        auth: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        注册自定义工具
        
        Args:
            name: 工具名称
            description: 工具描述
            parameters: 参数schema (JSON Schema格式)
            endpoint: 工具执行端点URL
            auth: 认证信息
        
        Returns:
            注册结果
        """
        payload = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "endpoint": endpoint,
        }
        
        if auth:
            payload["auth"] = auth
        
        response = self._request("POST", "/api/v1/sdk/tools/register", data=payload)
        return response.json()
    
    def list_tools(self) -> Dict[str, Any]:
        """
        列出所有可用工具
        
        Returns:
            工具列表
        """
        response = self._request("GET", "/api/v1/sdk/tools")
        return response.json()
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            健康状态
        """
        response = self._request("GET", "/api/v1/sdk/health")
        return response.json()


# ==================== 便捷函数 ====================

def create_client(
    app_id: str,
    app_secret: str,
    base_url: str = "http://localhost:8000",
    **kwargs
) -> ChatBotSDK:
    """
    创建ChatBot客户端
    
    用法:
        >>> client = create_client("my_app", "secret")
        >>> client.initialize()
        >>> response = client.chat("你好")
    """
    config = ChatBotConfig(
        app_id=app_id,
        app_secret=app_secret,
        base_url=base_url,
        **kwargs
    )
    return ChatBotSDK(config)


# ==================== 示例 ====================

if __name__ == "__main__":
    # 示例用法
    
    # 1. 创建客户端
    client = create_client(
        app_id="demo_app",
        app_secret="demo_secret",
        workspace_root="/path/to/workspace",
        mcp_servers=[
            {
                "name": "database_tools",
                "url": "http://localhost:9000"
            }
        ]
    )
    
    # 2. 初始化
    print("Initializing...")
    result = client.initialize()
    print(f"Initialized: {result}")
    
    # 3. 健康检查
    health = client.health_check()
    print(f"Health: {health}")
    
    # 4. 上传文档
    print("\nUploading document...")
    client.upload_document(
        content="这是一份产品说明文档...",
        filename="product_manual.md",
        metadata={"category": "docs"}
    )
    
    # 5. 注册工具
    print("\nRegistering tool...")
    client.register_tool(
        name="query_database",
        description="查询数据库",
        parameters={
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "SQL语句"}
            },
            "required": ["sql"]
        },
        endpoint="https://my-app.com/api/query"
    )
    
    # 6. 普通聊天
    print("\n=== 普通对话 ===")
    response = client.chat("你好，请介绍一下自己")
    print(response)
    
    # 7. 流式聊天
    print("\n=== 流式对话 ===")
    for chunk in client.chat("请帮我生成一份报告", stream=True):
        if chunk.get("type") == "text":
            print(chunk.get("content"), end="", flush=True)
    print()
    
    # 8. 使用@路径引用
    print("\n=== @路径引用 ===")
    response = client.chat("请分析 @/data/sales.csv 的内容")
    print(response)
    
    # 9. 列出工具
    print("\n=== 可用工具 ===")
    tools = client.list_tools()
    print(f"Tools: {tools}")

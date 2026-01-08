# -*- coding: utf-8 -*-
"""
Agentic ChatBot SDK - REST API 客户端

这是一个轻量级的 HTTP 封装，用于调用 Agentic ChatBot 后端服务。

使用前请确保后端服务已启动：
    cd backend && python run.py

使用示例：
    from agentic_sdk import ChatBot
    
    bot = ChatBot(base_url="http://localhost:8000")
    response = bot.chat("你好")
    print(response.text)
    
    # 流式对话
    for chunk in bot.chat_stream("讲个故事"):
        print(chunk.content, end="", flush=True)
"""
import json
from typing import Any, Dict, Iterator, List, Optional, Generator
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .types import ChatResponse, ChatChunk, IntentResult
from .exceptions import (
    AgenticSDKError,
    ConnectionError,
    AuthenticationError,
    APIError,
)


class ChatBot:
    """
    Agentic ChatBot SDK 客户端
    
    通过 REST API 与后端服务通信。
    
    Args:
        base_url: 后端服务地址（必填）
        api_key: API Key（可选，用于认证）
        timeout: 请求超时时间（秒）
        max_retries: 最大重试次数
    
    Example::
    
        from agentic_sdk import ChatBot
        
        # 基础用法
        bot = ChatBot(base_url="http://localhost:8000")
        response = bot.chat("你好")
        print(response.text)
        
        # 带认证
        bot = ChatBot(
            base_url="http://localhost:8000",
            api_key="your-api-key"
        )
        
        # 流式输出
        for chunk in bot.chat_stream("讲个故事"):
            print(chunk.content, end="", flush=True)
    """
    
    VERSION = "0.3.0"
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 3,
    ):
        if not base_url:
            raise ValueError(
                "base_url is required.\n"
                "Please start the backend first:\n"
                "  cd backend && python run.py"
            )
        
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        
        # 配置会话和重试
        self._session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"AgenticSDK/{self.VERSION}",
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        stream: bool = False,
    ) -> requests.Response:
        """发送 HTTP 请求"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self._session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout,
                stream=stream,
            )
            
            # 处理错误
            if response.status_code == 401:
                raise AuthenticationError("Authentication failed. Check your API key.")
            elif response.status_code == 403:
                raise AuthenticationError("Permission denied.")
            elif response.status_code >= 400:
                try:
                    error_data = response.json()
                    message = error_data.get("detail", {}).get("message", response.text)
                except:
                    message = response.text
                raise APIError(f"API error ({response.status_code}): {message}")
            
            return response
            
        except requests.ConnectionError as e:
            raise ConnectionError(
                f"Cannot connect to {self.base_url}. "
                "Is the backend running?\n"
                "Start it with: cd backend && python run.py"
            ) from e
        except requests.Timeout as e:
            raise ConnectionError(f"Request timeout after {self.timeout}s") from e
    
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """GET 请求"""
        response = self._request("GET", endpoint, params=params)
        return response.json()
    
    def _post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """POST 请求"""
        response = self._request("POST", endpoint, data=data)
        return response.json()
    
    def _delete(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """DELETE 请求"""
        response = self._request("DELETE", endpoint, params=params)
        return response.json()
    
    def _patch(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """PATCH 请求"""
        response = self._request("PATCH", endpoint, data=data)
        return response.json()
    
    # ==================== Chat API ====================
    
    def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        use_rag: bool = True,
    ) -> ChatResponse:
        """
        发送消息并获取回复
        
        Args:
            message: 用户消息
            session_id: 会话 ID（可选，用于多轮对话）
            use_rag: 是否使用 RAG 检索
        
        Returns:
            ChatResponse: 包含回复文本、来源等信息
        
        Example::
        
            response = bot.chat("你好")
            print(response.text)
            print(response.sources)  # RAG 来源
        """
        data = self._post("/api/v2/chat/message", {
            "message": message,
            "session_id": session_id,
            "use_rag": use_rag,
        })
        
        return ChatResponse(
            text=data.get("message", ""),
            session_id=data.get("session_id", session_id or ""),
            used_tools=data.get("used_tools", []),
            sources=data.get("citations", []),
            duration_ms=data.get("duration_ms", 0),
            intent=data.get("intent"),
        )
    
    def chat_stream(
        self,
        message: str,
        session_id: Optional[str] = None,
        use_rag: bool = True,
    ) -> Generator[ChatChunk, None, None]:
        """
        流式对话
        
        Args:
            message: 用户消息
            session_id: 会话 ID
            use_rag: 是否使用 RAG
        
        Yields:
            ChatChunk: 响应块
        
        Example::
        
            for chunk in bot.chat_stream("讲个故事"):
                if chunk.type == "text":
                    print(chunk.content, end="", flush=True)
        """
        response = self._request(
            "POST",
            "/api/v2/chat/stream",
            data={
                "message": message,
                "session_id": session_id,
                "use_rag": use_rag,
            },
            stream=True,
        )
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data_str = line[6:]
                    if data_str.strip() == '[DONE]':
                        break
                    try:
                        data = json.loads(data_str)
                        yield ChatChunk(
                            type=data.get("type", "text"),
                            content=data.get("content", ""),
                            metadata=data.get("metadata"),
                        )
                    except json.JSONDecodeError:
                        continue
    
    def analyze_intent(self, message: str) -> IntentResult:
        """
        分析用户意图
        
        Args:
            message: 用户消息
        
        Returns:
            IntentResult: 意图分析结果
        """
        data = self._post("/api/v2/chat/analyze-intent", {
            "message": message,
        })
        
        return IntentResult(
            surface_intent=data.get("surface_intent", ""),
            deep_intent=data.get("deep_intent", ""),
            task_type=data.get("task_type", ""),
            complexity=data.get("complexity", ""),
            is_multi_step=data.get("is_multi_step", False),
            suggested_tools=data.get("suggested_tools", []),
            confidence=data.get("confidence", 0.0),
        )
    
    def submit_feedback(
        self,
        session_id: str,
        feedback: str,
    ) -> bool:
        """
        提交反馈
        
        Args:
            session_id: 会话 ID
            feedback: "positive" 或 "negative"
        
        Returns:
            是否成功
        """
        if feedback not in ["positive", "negative"]:
            raise ValueError("feedback must be 'positive' or 'negative'")
        
        data = self._post(f"/api/v2/chat/feedback/{session_id}?feedback={feedback}")
        return "message" in data
    
    def clear_session(self, session_id: str) -> bool:
        """清除会话"""
        data = self._delete(f"/api/v2/chat/session/{session_id}")
        return "message" in data
    
    def get_stats(self) -> Dict[str, Any]:
        """获取系统统计"""
        return self._get("/api/v2/chat/stats")
    
    # ==================== Documents API ====================
    
    def list_documents(
        self,
        page: int = 1,
        page_size: int = 20,
        file_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        列出文档
        
        Args:
            page: 页码
            page_size: 每页数量
            file_type: 文件类型过滤
        
        Returns:
            包含 documents, total, page 等字段
        """
        params = {"page": page, "page_size": page_size}
        if file_type:
            params["file_type"] = file_type
        return self._get("/api/v2/documents/list", params=params)
    
    def search_documents(
        self,
        query: str,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        搜索文档
        
        Args:
            query: 搜索查询
            top_k: 返回结果数量
        
        Returns:
            搜索结果
        """
        return self._post("/api/v2/documents/search", {
            "query": query,
            "top_k": top_k,
        })
    
    def get_document(self, document_id: str) -> Dict[str, Any]:
        """获取文档详情"""
        return self._get(f"/api/v2/documents/{document_id}")
    
    def delete_document(self, document_id: str) -> bool:
        """删除文档"""
        data = self._delete(f"/api/v2/documents/{document_id}")
        return "message" in data
    
    # ==================== Settings API ====================
    
    def get_index_status(self, workspace: str = ".") -> Dict[str, Any]:
        """获取索引状态"""
        return self._get("/api/v2/settings/indexing/status", {"workspace": workspace})
    
    def sync_index(self, force: bool = False, workspace: str = ".") -> Dict[str, Any]:
        """同步索引"""
        return self._post(
            f"/api/v2/settings/indexing/sync?workspace={workspace}",
            {"force": force, "priority_only": False}
        )
    
    def clear_index(self, workspace: str = ".") -> bool:
        """清除索引"""
        data = self._delete(f"/api/v2/settings/indexing?workspace={workspace}")
        return data.get("success", False)
    
    def get_rules(self) -> Dict[str, List[str]]:
        """获取规则"""
        return self._get("/api/v2/settings/rules")
    
    def add_rule(self, content: str, rule_type: str = "user") -> bool:
        """添加规则"""
        data = self._post("/api/v2/settings/rules", {
            "content": content,
            "type": rule_type,
        })
        return data.get("success", False)
    
    def remove_rule(self, content: str, rule_type: str = "user") -> bool:
        """删除规则"""
        data = self._delete(
            "/api/v2/settings/rules",
            {"content": content, "type": rule_type}
        )
        return data.get("success", False)
    
    def list_skills(self) -> List[Dict[str, Any]]:
        """列出技能"""
        data = self._get("/api/v2/settings/skills")
        return data.get("skills", [])
    
    def get_skill(self, skill_id: str) -> Dict[str, Any]:
        """获取技能详情"""
        return self._get(f"/api/v2/settings/skills/{skill_id}")
    
    def create_skill(
        self,
        skill_id: str,
        name: str,
        description: str,
        instructions: str,
        triggers: List[str],
        category: str = "custom",
    ) -> bool:
        """创建技能"""
        data = self._post("/api/v2/settings/skills", {
            "id": skill_id,
            "name": name,
            "description": description,
            "instructions": instructions,
            "triggers": triggers,
            "category": category,
        })
        return data.get("success", False)
    
    def update_skill(
        self,
        skill_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        triggers: Optional[List[str]] = None,
        enabled: Optional[bool] = None,
    ) -> bool:
        """更新技能"""
        payload = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if instructions is not None:
            payload["instructions"] = instructions
        if triggers is not None:
            payload["triggers"] = triggers
        if enabled is not None:
            payload["enabled"] = enabled
        
        data = self._patch(f"/api/v2/settings/skills/{skill_id}", payload)
        return data.get("success", False)
    
    def toggle_skill(self, skill_id: str, enabled: bool) -> bool:
        """启用/禁用技能"""
        data = self._post(f"/api/v2/settings/skills/{skill_id}/toggle?enabled={enabled}")
        return data.get("success", False)
    
    def delete_skill(self, skill_id: str) -> bool:
        """删除技能"""
        data = self._delete(f"/api/v2/settings/skills/{skill_id}")
        return data.get("success", False)
    
    def list_mcp_servers(self) -> List[Dict[str, Any]]:
        """列出 MCP 服务器"""
        data = self._get("/api/v2/settings/mcp")
        return data.get("servers", [])
    
    def add_mcp_server(
        self,
        name: str,
        server_type: str,
        url: Optional[str] = None,
    ) -> bool:
        """添加 MCP 服务器"""
        data = self._post("/api/v2/settings/mcp", {
            "name": name,
            "server_type": server_type,
            "url": url,
        })
        return data.get("success", False)
    
    def remove_mcp_server(self, name: str) -> bool:
        """删除 MCP 服务器"""
        data = self._delete(f"/api/v2/settings/mcp/{name}")
        return data.get("success", False)
    
    def get_settings_summary(self, workspace: str = ".") -> Dict[str, Any]:
        """获取设置摘要"""
        return self._get(f"/api/v2/settings/summary?workspace={workspace}")
    
    # ==================== Batch API ====================
    
    def chat_batch(
        self,
        messages: List[str],
        session_id: Optional[str] = None,
        parallel: bool = True,
    ) -> List[ChatResponse]:
        """
        批量对话
        
        Args:
            messages: 消息列表
            session_id: 共享会话 ID
            parallel: 是否并行处理
        
        Returns:
            响应列表
        """
        requests_data = [
            {"message": msg, "session_id": session_id}
            for msg in messages
        ]
        
        data = self._post("/api/v2/batch/chat", {
            "requests": requests_data,
            "parallel": parallel,
        })
        
        responses = []
        for r in data.get("results", []):
            if r.get("success"):
                responses.append(ChatResponse(
                    text=r.get("message", ""),
                    session_id=r.get("session_id", ""),
                    used_tools=r.get("used_tools", []),
                ))
            else:
                responses.append(ChatResponse(
                    text=f"Error: {r.get('error', 'Unknown error')}",
                    session_id="",
                ))
        
        return responses
    
    # ==================== Utility ====================
    
    def health_check(self) -> Dict[str, Any]:
        """检查后端服务健康状态"""
        url = f"{self.base_url}/health"
        try:
            response = self._session.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            return response.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def close(self):
        """关闭连接"""
        self._session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def __repr__(self):
        return f"ChatBot(base_url='{self.base_url}')"


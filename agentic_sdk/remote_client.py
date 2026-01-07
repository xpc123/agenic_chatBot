# -*- coding: utf-8 -*-
"""
远程客户端 - 通过 HTTP API 与后端通信
"""
import hmac
import hashlib
import time
import json
from typing import Any, Dict, Iterator, List, Optional

import requests
from loguru import logger

from .config import ChatConfig
from .types import ChatResponse, ChatChunk, ToolCall


class RemoteClient:
    """
    远程客户端
    
    通过 HTTP API 与后端通信，支持：
    - 对话 (chat)
    - 流式输出 (stream)
    - 设置管理 (settings)
    """
    
    def __init__(self, config: ChatConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        self._initialized = False
    
    def _generate_signature(self, timestamp: int, body: str) -> str:
        """生成 HMAC-SHA256 签名"""
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
            "Content-Type": "application/json",
            "X-App-Id": self.config.app_id,
            "X-Timestamp": str(timestamp),
            "X-Signature": self._generate_signature(timestamp, body),
        }
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        stream: bool = False,
    ) -> requests.Response:
        """发送 HTTP 请求"""
        url = f"{self.config.base_url}{endpoint}"
        body = json.dumps(data) if data else ""
        headers = self._get_headers(body)
        
        response = self.session.request(
            method=method,
            url=url,
            data=body if body else None,
            headers=headers,
            timeout=self.config.timeout,
            stream=stream,
        )
        
        response.raise_for_status()
        return response
    
    def initialize(self) -> Dict[str, Any]:
        """初始化"""
        if self._initialized:
            return {"status": "already_initialized"}
        
        try:
            response = self._request("GET", "/api/v1/health")
            self._initialized = True
            logger.info(f"Remote client connected to {self.config.base_url}")
            return response.json()
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise
    
    # ==================== Chat API ====================
    
    def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        use_rag: bool = True,
        context: Optional[Dict[str, Any]] = None,
    ) -> ChatResponse:
        """同步对话"""
        payload = {
            "message": message,
            "session_id": session_id,
            "stream": False,
            "use_rag": use_rag,
        }
        if context:
            payload["context"] = context
        
        response = self._request("POST", "/api/v1/sdk/chat", data=payload)
        data = response.json()
        
        return ChatResponse(
            text=data.get("response", ""),
            tool_calls=[],
            sources=data.get("sources", []),
            session_id=data.get("session_id", session_id),
            latency_ms=data.get("latency_ms", 0),
        )
    
    def chat_stream(
        self,
        message: str,
        session_id: Optional[str] = None,
        use_rag: bool = True,
    ) -> Iterator[ChatChunk]:
        """流式对话"""
        payload = {
            "message": message,
            "session_id": session_id,
            "stream": True,
            "use_rag": use_rag,
        }
        
        response = self._request("POST", "/api/v1/sdk/chat", data=payload, stream=True)
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]
                    if data.strip() == '[DONE]':
                        break
                    try:
                        chunk_data = json.loads(data)
                        yield ChatChunk(
                            type=chunk_data.get("type", "text"),
                            content=chunk_data.get("content", ""),
                            is_final=chunk_data.get("is_final", False),
                        )
                    except json.JSONDecodeError:
                        continue
    
    # ==================== Settings API ====================
    
    def get_indexing_status(self, workspace: str = ".") -> Dict[str, Any]:
        """获取索引状态"""
        response = self._request("GET", f"/api/v1/settings/indexing/status?workspace={workspace}")
        return response.json()
    
    def sync_index(self, force: bool = False, workspace: str = ".") -> Dict[str, Any]:
        """同步索引"""
        payload = {"force": force, "priority_only": False}
        response = self._request("POST", f"/api/v1/settings/indexing/sync?workspace={workspace}", data=payload)
        return response.json()
    
    def clear_index(self, workspace: str = ".") -> Dict[str, Any]:
        """清除索引"""
        response = self._request("DELETE", f"/api/v1/settings/indexing?workspace={workspace}")
        return response.json()
    
    # Rules
    def get_rules(self) -> Dict[str, Any]:
        """获取规则"""
        response = self._request("GET", "/api/v1/settings/rules")
        return response.json()
    
    def add_rule(self, content: str, rule_type: str = "user") -> Dict[str, Any]:
        """添加规则"""
        payload = {"content": content, "type": rule_type}
        response = self._request("POST", "/api/v1/settings/rules", data=payload)
        return response.json()
    
    def remove_rule(self, content: str, rule_type: str = "user") -> Dict[str, Any]:
        """删除规则"""
        response = self._request("DELETE", f"/api/v1/settings/rules?content={content}&type={rule_type}")
        return response.json()
    
    # Skills
    def list_skills(self) -> Dict[str, Any]:
        """获取技能列表"""
        response = self._request("GET", "/api/v1/settings/skills")
        return response.json()
    
    def get_skill(self, skill_id: str) -> Dict[str, Any]:
        """获取技能详情"""
        response = self._request("GET", f"/api/v1/settings/skills/{skill_id}")
        return response.json()
    
    def create_skill(
        self,
        skill_id: str,
        name: str,
        description: str,
        instructions: str,
        triggers: List[str],
        category: str = "custom",
    ) -> Dict[str, Any]:
        """创建技能"""
        payload = {
            "id": skill_id,
            "name": name,
            "description": description,
            "instructions": instructions,
            "triggers": triggers,
            "category": category,
        }
        response = self._request("POST", "/api/v1/settings/skills", data=payload)
        return response.json()
    
    def toggle_skill(self, skill_id: str, enabled: bool) -> Dict[str, Any]:
        """启用/禁用技能"""
        response = self._request("POST", f"/api/v1/settings/skills/{skill_id}/toggle?enabled={enabled}")
        return response.json()
    
    def delete_skill(self, skill_id: str) -> Dict[str, Any]:
        """删除技能"""
        response = self._request("DELETE", f"/api/v1/settings/skills/{skill_id}")
        return response.json()
    
    # MCP
    def list_mcp_servers(self) -> Dict[str, Any]:
        """获取 MCP 服务器列表"""
        response = self._request("GET", "/api/v1/settings/mcp")
        return response.json()
    
    def add_mcp_server(
        self,
        name: str,
        server_type: str,
        url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """添加 MCP 服务器"""
        payload = {"name": name, "server_type": server_type, "url": url}
        response = self._request("POST", "/api/v1/settings/mcp", data=payload)
        return response.json()
    
    def remove_mcp_server(self, name: str) -> Dict[str, Any]:
        """删除 MCP 服务器"""
        response = self._request("DELETE", f"/api/v1/settings/mcp/{name}")
        return response.json()
    
    # Summary
    def get_settings_summary(self, workspace: str = ".") -> Dict[str, Any]:
        """获取设置摘要"""
        response = self._request("GET", f"/api/v1/settings/summary?workspace={workspace}")
        return response.json()






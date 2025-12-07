"""
上下文配置加载器
用于方式二（独立GUI）的配置管理
"""
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
from loguru import logger
from pydantic import BaseModel, Field


class RAGSourceConfig(BaseModel):
    """RAG数据源配置"""
    paths: List[str] = Field(default_factory=list, description="文档路径列表")


class MCPServerConfig(BaseModel):
    """MCP服务器配置"""
    name: str
    type: str  # sqlite, http, custom
    config: Dict[str, Any]
    enabled: bool = True


class UIConfig(BaseModel):
    """UI配置"""
    theme: str = "light"
    primary_color: str = "#4F46E5"
    title: str = "Agentic ChatBot"
    welcome_message: str = "你好！有什么可以帮您的吗？"
    placeholder: str = "输入您的问题..."


class FeaturesConfig(BaseModel):
    """功能配置"""
    enable_rag: bool = True
    enable_planning: bool = True
    enable_path_reference: bool = True
    enable_mcp_tools: bool = True
    max_conversation_history: int = 50


class SecurityConfig(BaseModel):
    """安全配置"""
    allowed_domains: List[str] = Field(default_factory=lambda: ["localhost"])
    max_file_size_mb: int = 10
    rate_limit: Optional[Dict[str, int]] = None


class ContextConfig(BaseModel):
    """上下文配置"""
    rag_sources: List[str] = Field(default_factory=list)
    path_whitelist: List[str] = Field(default_factory=list)
    mcp_servers: List[MCPServerConfig] = Field(default_factory=list)


class AppConfig(BaseModel):
    """应用配置"""
    app_name: str = "Agentic ChatBot"
    description: str = ""
    context: ContextConfig = Field(default_factory=ContextConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)


class ConfigLoader:
    """配置加载器"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path or "./config.json")
        self._config: Optional[AppConfig] = None
    
    def load(self) -> AppConfig:
        """
        加载配置文件
        
        Returns:
            应用配置对象
        """
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}, using defaults")
            return AppConfig()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 环境变量替换
            config_data = self._replace_env_vars(config_data)
            
            self._config = AppConfig(**config_data)
            logger.info(f"Configuration loaded from {self.config_path}")
            
            return self._config
        
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            logger.warning("Using default configuration")
            return AppConfig()
    
    def _replace_env_vars(self, data: Any) -> Any:
        """
        递归替换配置中的环境变量
        
        支持格式: ${ENV_VAR} 或 ${ENV_VAR:default_value}
        """
        import os
        import re
        
        if isinstance(data, dict):
            return {k: self._replace_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._replace_env_vars(item) for item in data]
        elif isinstance(data, str):
            # 查找 ${VAR} 或 ${VAR:default} 模式
            pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
            
            def replace_match(match):
                var_name = match.group(1)
                default_value = match.group(2) or ""
                return os.getenv(var_name, default_value)
            
            return re.sub(pattern, replace_match, data)
        else:
            return data
    
    def get_config(self) -> AppConfig:
        """获取已加载的配置"""
        if self._config is None:
            self._config = self.load()
        return self._config
    
    def reload(self) -> AppConfig:
        """重新加载配置"""
        self._config = None
        return self.load()
    
    def validate_paths(self) -> Dict[str, Any]:
        """
        验证配置中的路径
        
        Returns:
            验证结果
        """
        config = self.get_config()
        results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # 验证RAG源
        for source in config.context.rag_sources:
            path = Path(source)
            if not path.exists():
                results["warnings"].append(f"RAG source not found: {source}")
        
        # 验证MCP服务器配置
        for server in config.context.mcp_servers:
            if server.type == "sqlite":
                db_path = server.config.get("database_path")
                if db_path and not Path(db_path).exists():
                    results["warnings"].append(f"Database not found: {db_path}")
        
        return results


# 全局配置实例
_config_loader: Optional[ConfigLoader] = None


def get_config_loader(config_path: Optional[str] = None) -> ConfigLoader:
    """获取全局配置加载器实例"""
    global _config_loader
    
    if _config_loader is None:
        _config_loader = ConfigLoader(config_path)
    
    return _config_loader


def get_app_config() -> AppConfig:
    """快捷方式：获取应用配置"""
    return get_config_loader().get_config()

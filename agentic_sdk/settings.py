# -*- coding: utf-8 -*-
"""
Settings API - SDK 设置接口

提供与 Gradio Settings UI 对应的 SDK 接口：
1. Indexing & Docs - 索引和文档管理
2. Rules & Commands - 规则和命令
3. Skills - 技能管理
4. Tools & MCP - 工具和 MCP 服务器
"""
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from loguru import logger

# 添加 backend 路径
BACKEND_PATH = Path(__file__).parent.parent / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))


# ==================== 数据类 ====================

@dataclass
class IndexingStatus:
    """索引状态"""
    total_files: int = 0
    indexed_files: int = 0
    skipped_files: int = 0
    failed_files: int = 0
    is_complete: bool = False
    current_file: Optional[str] = None


@dataclass
class SkillInfo:
    """技能信息"""
    id: str
    name: str
    description: str
    triggers: List[str]
    enabled: bool = True
    category: str = "general"


@dataclass
class RuleInfo:
    """规则信息"""
    content: str
    type: str  # "user" or "project"


@dataclass
class MCPServerInfo:
    """MCP 服务器信息"""
    name: str
    server_type: str
    url: Optional[str] = None
    status: str = "unknown"


# ==================== Settings Manager ====================

class SettingsManager:
    """
    SDK 设置管理器
    
    对应 Gradio Settings UI 的功能：
    - 索引管理
    - 规则管理
    - 技能管理
    - MCP 工具管理
    
    Example::
    
        from agentic_sdk import SettingsManager
        
        settings = SettingsManager(workspace="/path/to/project")
        
        # 索引管理
        status = settings.sync_index()
        files = settings.get_indexed_files()
        
        # 规则管理
        settings.add_user_rule("始终使用中文回复")
        settings.add_project_rule("使用 FastAPI 风格")
        
        # 技能管理
        skills = settings.list_skills()
        settings.toggle_skill("code_review", enabled=True)
        
        # MCP 管理
        settings.add_mcp_server("my-server", "http", "http://localhost:9000")
    """
    
    def __init__(self, workspace: Optional[str] = None):
        """
        初始化设置管理器
        
        Args:
            workspace: 工作区路径，默认为当前目录
        """
        self.workspace = Path(workspace or ".").resolve()
        self._indexer = None
        self._skills_manager = None
        self._settings_file = self.workspace / ".agentic_chatbot" / "settings.json"
        self._settings: Dict[str, Any] = self._load_settings()
        
        logger.info(f"SettingsManager initialized for workspace: {self.workspace}")
    
    def _load_settings(self) -> Dict[str, Any]:
        """加载设置"""
        import json
        
        default = {
            "indexing": {
                "enabled": True,
                "auto_index": True,
            },
            "rules": {
                "user_rules": [],
                "project_rules": [],
            },
            "mcp_servers": [],
            "docs": [],
        }
        
        if self._settings_file.exists():
            try:
                with open(self._settings_file, 'r') as f:
                    loaded = json.load(f)
                    return {**default, **loaded}
            except Exception as e:
                logger.warning(f"Failed to load settings: {e}")
        
        return default
    
    def _save_settings(self):
        """保存设置"""
        import json
        
        self._settings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._settings_file, 'w') as f:
            json.dump(self._settings, f, indent=2, ensure_ascii=False)
    
    def _get_indexer(self):
        """获取索引器"""
        if self._indexer is None:
            from app.rag.workspace_indexer import get_workspace_indexer
            self._indexer = get_workspace_indexer(str(self.workspace))
        return self._indexer
    
    def _get_skills_manager(self):
        """获取技能管理器"""
        if self._skills_manager is None:
            from app.core.skills import SkillsManager
            self._skills_manager = SkillsManager()
        return self._skills_manager
    
    # ==================== 1. Indexing & Docs ====================
    
    def sync_index(self, force: bool = False) -> IndexingStatus:
        """
        同步索引
        
        Args:
            force: 是否强制重新索引
        
        Returns:
            IndexingStatus: 索引状态
        
        Example::
        
            status = settings.sync_index()
            print(f"Indexed {status.indexed_files} files")
        """
        import asyncio
        
        async def _sync():
            indexer = self._get_indexer()
            return await indexer.index_workspace(force=force)
        
        loop = asyncio.new_event_loop()
        try:
            status = loop.run_until_complete(_sync())
            return IndexingStatus(
                total_files=status.total_files,
                indexed_files=status.indexed_files,
                skipped_files=status.skipped_files,
                failed_files=status.failed_files,
                is_complete=status.is_complete,
            )
        finally:
            loop.close()
    
    def get_indexed_files(self) -> List[str]:
        """
        获取已索引文件列表
        
        Returns:
            List[str]: 文件路径列表
        """
        indexer = self._get_indexer()
        return indexer.get_indexed_files()
    
    def get_index_status(self) -> IndexingStatus:
        """
        获取索引状态
        
        Returns:
            IndexingStatus: 当前索引状态
        """
        indexer = self._get_indexer()
        status = indexer.get_status()
        return IndexingStatus(
            total_files=status.total_files,
            indexed_files=status.indexed_files,
            skipped_files=status.skipped_files,
            failed_files=status.failed_files,
            is_complete=status.is_complete,
            current_file=status.current_file,
        )
    
    def clear_index(self) -> bool:
        """
        清除索引
        
        Returns:
            bool: 是否成功
        """
        try:
            indexer = self._get_indexer()
            indexer.clear_index()
            return True
        except Exception as e:
            logger.error(f"Failed to clear index: {e}")
            return False
    
    def add_doc(self, path: str) -> bool:
        """
        添加文档到知识库
        
        Args:
            path: 文档路径
        
        Returns:
            bool: 是否成功
        """
        if path not in self._settings["docs"]:
            self._settings["docs"].append(path)
            self._save_settings()
        return True
    
    def remove_doc(self, path: str) -> bool:
        """删除文档"""
        if path in self._settings["docs"]:
            self._settings["docs"].remove(path)
            self._save_settings()
        return True
    
    def get_docs(self) -> List[str]:
        """获取文档列表"""
        return self._settings.get("docs", [])
    
    # ==================== 2. Rules & Commands ====================
    
    def add_user_rule(self, rule: str) -> bool:
        """
        添加用户规则
        
        Args:
            rule: 规则内容（如 "始终使用中文回复"）
        
        Returns:
            bool: 是否成功
        
        Example::
        
            settings.add_user_rule("代码注释使用英文")
        """
        rules = self._settings["rules"]["user_rules"]
        if rule not in rules:
            rules.append(rule)
            self._save_settings()
        return True
    
    def remove_user_rule(self, rule: str) -> bool:
        """删除用户规则"""
        rules = self._settings["rules"]["user_rules"]
        if rule in rules:
            rules.remove(rule)
            self._save_settings()
        return True
    
    def get_user_rules(self) -> List[str]:
        """获取用户规则列表"""
        return self._settings["rules"]["user_rules"]
    
    def add_project_rule(self, rule: str) -> bool:
        """
        添加项目规则
        
        Args:
            rule: 规则内容（如 "使用 FastAPI 风格"）
        
        Returns:
            bool: 是否成功
        """
        rules = self._settings["rules"]["project_rules"]
        if rule not in rules:
            rules.append(rule)
            self._save_settings()
        return True
    
    def remove_project_rule(self, rule: str) -> bool:
        """删除项目规则"""
        rules = self._settings["rules"]["project_rules"]
        if rule in rules:
            rules.remove(rule)
            self._save_settings()
        return True
    
    def get_project_rules(self) -> List[str]:
        """获取项目规则列表"""
        return self._settings["rules"]["project_rules"]
    
    def get_all_rules(self) -> List[RuleInfo]:
        """获取所有规则"""
        rules = []
        for r in self.get_user_rules():
            rules.append(RuleInfo(content=r, type="user"))
        for r in self.get_project_rules():
            rules.append(RuleInfo(content=r, type="project"))
        return rules
    
    # ==================== 3. Skills ====================
    
    def list_skills(self) -> List[SkillInfo]:
        """
        获取所有技能
        
        Returns:
            List[SkillInfo]: 技能列表
        
        Example::
        
            for skill in settings.list_skills():
                print(f"{skill.name}: {skill.description}")
        """
        manager = self._get_skills_manager()
        skills = manager.list_skills()
        
        return [
            SkillInfo(
                id=s.id,
                name=s.name,
                description=s.description,
                triggers=s.triggers,
                enabled=s.enabled,
                category=s.category,
            )
            for s in skills
        ]
    
    def get_skill(self, skill_id: str) -> Optional[SkillInfo]:
        """获取单个技能"""
        manager = self._get_skills_manager()
        skill = manager.get_skill(skill_id)
        
        if skill:
            return SkillInfo(
                id=skill.id,
                name=skill.name,
                description=skill.description,
                triggers=skill.triggers,
                enabled=skill.enabled,
                category=skill.category,
            )
        return None
    
    def toggle_skill(self, skill_id: str, enabled: bool) -> bool:
        """
        启用/禁用技能
        
        Args:
            skill_id: 技能 ID
            enabled: 是否启用
        
        Returns:
            bool: 是否成功
        """
        manager = self._get_skills_manager()
        skill = manager.get_skill(skill_id)
        
        if skill:
            skill.enabled = enabled
            manager.add_skill(skill)
            return True
        return False
    
    def create_skill(
        self,
        skill_id: str,
        name: str,
        description: str,
        instructions: str,
        triggers: List[str],
        category: str = "custom",
    ) -> bool:
        """
        创建自定义技能
        
        Args:
            skill_id: 技能 ID
            name: 技能名称
            description: 描述
            instructions: 详细指令
            triggers: 触发词列表
            category: 分类
        
        Returns:
            bool: 是否成功
        
        Example::
        
            settings.create_skill(
                skill_id="my_skill",
                name="我的技能",
                description="自定义技能",
                instructions="作为专家，请...",
                triggers=["关键词1", "关键词2"],
            )
        """
        from app.core.skills import Skill
        
        manager = self._get_skills_manager()
        
        skill = Skill(
            id=skill_id,
            name=name,
            description=description,
            instructions=instructions,
            triggers=triggers,
            category=category,
        )
        
        manager.add_skill(skill)
        return True
    
    def delete_skill(self, skill_id: str) -> bool:
        """删除技能（只能删除自定义技能）"""
        manager = self._get_skills_manager()
        return manager.remove_skill(skill_id)
    
    # ==================== 4. Tools & MCP ====================
    
    def add_mcp_server(
        self,
        name: str,
        server_type: str,
        url: Optional[str] = None,
    ) -> bool:
        """
        添加 MCP 服务器
        
        Args:
            name: 服务器名称
            server_type: 类型（http, sqlite, custom）
            url: 服务器 URL
        
        Returns:
            bool: 是否成功
        
        Example::
        
            settings.add_mcp_server(
                name="my-mcp",
                server_type="http",
                url="http://localhost:9000"
            )
        """
        server = {
            "name": name,
            "type": server_type,
            "url": url,
        }
        
        # 检查是否已存在
        for s in self._settings["mcp_servers"]:
            if s.get("name") == name:
                return False
        
        self._settings["mcp_servers"].append(server)
        self._save_settings()
        return True
    
    def remove_mcp_server(self, name: str) -> bool:
        """删除 MCP 服务器"""
        self._settings["mcp_servers"] = [
            s for s in self._settings["mcp_servers"]
            if s.get("name") != name
        ]
        self._save_settings()
        return True
    
    def list_mcp_servers(self) -> List[MCPServerInfo]:
        """获取 MCP 服务器列表"""
        return [
            MCPServerInfo(
                name=s.get("name", ""),
                server_type=s.get("type", "unknown"),
                url=s.get("url"),
            )
            for s in self._settings.get("mcp_servers", [])
        ]
    
    # ==================== 便捷方法 ====================
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取设置摘要
        
        Returns:
            Dict: 设置摘要
        """
        return {
            "workspace": str(self.workspace),
            "indexed_files": len(self.get_indexed_files()),
            "user_rules": len(self.get_user_rules()),
            "project_rules": len(self.get_project_rules()),
            "skills": len(self.list_skills()),
            "mcp_servers": len(self.list_mcp_servers()),
            "docs": len(self.get_docs()),
        }


# ==================== 便捷函数 ====================

def get_settings_manager(workspace: Optional[str] = None) -> SettingsManager:
    """获取设置管理器实例"""
    return SettingsManager(workspace)


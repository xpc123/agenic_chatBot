# -*- coding: utf-8 -*-
"""
Settings API - 设置管理接口

提供以下功能的 HTTP API:
- 索引管理 (Indexing)
- 规则管理 (Rules)
- 技能管理 (Skills)
- MCP 服务器管理 (MCP Servers)
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from loguru import logger

from ..core.skills import SkillsManager, Skill, get_skills_manager
from ..rag.workspace_indexer import get_workspace_indexer, IndexingStatus


router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


# ==================== Pydantic Models ====================

class RuleCreate(BaseModel):
    content: str
    type: str = "user"  # "user" or "project"


class SkillCreate(BaseModel):
    id: str
    name: str
    description: str
    instructions: str
    triggers: List[str]
    category: str = "custom"
    enabled: bool = True


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    triggers: Optional[List[str]] = None
    enabled: Optional[bool] = None


class MCPServerCreate(BaseModel):
    name: str
    server_type: str
    url: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class IndexingConfig(BaseModel):
    force: bool = False
    priority_only: bool = False


# ==================== 存储 ====================

# 简单的内存存储（生产环境应使用数据库）
_rules_store: Dict[str, List[str]] = {
    "user_rules": [],
    "project_rules": [],
}

_mcp_servers: List[Dict[str, Any]] = []


# ==================== Indexing API ====================

@router.get("/indexing/status")
async def get_indexing_status(workspace: str = ".") -> Dict[str, Any]:
    """获取索引状态"""
    try:
        indexer = get_workspace_indexer(workspace)
        status = indexer.get_status()
        indexed_files = indexer.get_indexed_files()
        
        return {
            "status": "complete" if status.is_complete else "in_progress",
            "total_files": status.total_files,
            "indexed_files": status.indexed_files,
            "skipped_files": status.skipped_files,
            "failed_files": status.failed_files,
            "current_file": status.current_file,
            "files": indexed_files[:100],  # 限制返回数量
            "total_indexed": len(indexed_files),
        }
    except Exception as e:
        logger.error(f"Get indexing status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/indexing/sync")
async def sync_index(
    config: IndexingConfig,
    workspace: str = ".",
    background_tasks: BackgroundTasks = None,
) -> Dict[str, Any]:
    """同步索引"""
    try:
        indexer = get_workspace_indexer(workspace)
        
        # 在后台执行索引
        async def do_index():
            return await indexer.index_workspace(
                force=config.force,
                priority_only=config.priority_only,
            )
        
        import asyncio
        status = await do_index()
        
        return {
            "success": True,
            "message": f"索引完成：{status.indexed_files} 个文件",
            "indexed_files": status.indexed_files,
            "skipped_files": status.skipped_files,
            "failed_files": status.failed_files,
        }
    except Exception as e:
        logger.error(f"Sync index failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/indexing")
async def clear_index(workspace: str = ".") -> Dict[str, Any]:
    """清除索引"""
    try:
        indexer = get_workspace_indexer(workspace)
        indexer.clear_index()
        return {"success": True, "message": "索引已清除"}
    except Exception as e:
        logger.error(f"Clear index failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Rules API ====================

@router.get("/rules")
async def list_rules() -> Dict[str, Any]:
    """获取所有规则"""
    return {
        "user_rules": _rules_store["user_rules"],
        "project_rules": _rules_store["project_rules"],
    }


@router.post("/rules")
async def add_rule(rule: RuleCreate) -> Dict[str, Any]:
    """添加规则"""
    key = f"{rule.type}_rules"
    if key not in _rules_store:
        raise HTTPException(status_code=400, detail=f"Invalid rule type: {rule.type}")
    
    if rule.content not in _rules_store[key]:
        _rules_store[key].append(rule.content)
    
    return {"success": True, "rule": rule.content, "type": rule.type}


@router.delete("/rules")
async def remove_rule(content: str, type: str = "user") -> Dict[str, Any]:
    """删除规则"""
    key = f"{type}_rules"
    if key not in _rules_store:
        raise HTTPException(status_code=400, detail=f"Invalid rule type: {type}")
    
    if content in _rules_store[key]:
        _rules_store[key].remove(content)
        return {"success": True, "message": "规则已删除"}
    
    return {"success": False, "message": "规则不存在"}


# ==================== Skills API ====================

@router.get("/skills")
async def list_skills() -> Dict[str, Any]:
    """获取所有技能"""
    manager = get_skills_manager()
    skills = manager.list_skills()
    
    return {
        "skills": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "triggers": s.triggers,
                "category": s.category,
                "enabled": s.enabled,
            }
            for s in skills
        ],
        "total": len(skills),
    }


@router.get("/skills/{skill_id}")
async def get_skill(skill_id: str) -> Dict[str, Any]:
    """获取单个技能详情"""
    manager = get_skills_manager()
    skill = manager.get_skill(skill_id)
    
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
    
    return {
        "id": skill.id,
        "name": skill.name,
        "description": skill.description,
        "instructions": skill.instructions,
        "triggers": skill.triggers,
        "category": skill.category,
        "enabled": skill.enabled,
    }


@router.post("/skills")
async def create_skill(skill: SkillCreate) -> Dict[str, Any]:
    """创建技能"""
    manager = get_skills_manager()
    
    new_skill = Skill(
        id=skill.id,
        name=skill.name,
        description=skill.description,
        instructions=skill.instructions,
        triggers=skill.triggers,
        category=skill.category,
        enabled=skill.enabled,
    )
    
    manager.add_skill(new_skill)
    
    return {"success": True, "skill_id": skill.id, "message": "技能已创建"}


@router.patch("/skills/{skill_id}")
async def update_skill(skill_id: str, updates: SkillUpdate) -> Dict[str, Any]:
    """更新技能"""
    manager = get_skills_manager()
    skill = manager.get_skill(skill_id)
    
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
    
    # 更新字段
    if updates.name is not None:
        skill.name = updates.name
    if updates.description is not None:
        skill.description = updates.description
    if updates.instructions is not None:
        skill.instructions = updates.instructions
    if updates.triggers is not None:
        skill.triggers = updates.triggers
    if updates.enabled is not None:
        skill.enabled = updates.enabled
    
    manager.add_skill(skill)
    
    return {"success": True, "skill_id": skill_id, "message": "技能已更新"}


@router.delete("/skills/{skill_id}")
async def delete_skill(skill_id: str) -> Dict[str, Any]:
    """删除技能"""
    manager = get_skills_manager()
    
    if manager.remove_skill(skill_id):
        return {"success": True, "message": "技能已删除"}
    else:
        raise HTTPException(status_code=404, detail=f"Skill not found or cannot be deleted: {skill_id}")


@router.post("/skills/{skill_id}/toggle")
async def toggle_skill(skill_id: str, enabled: bool) -> Dict[str, Any]:
    """启用/禁用技能"""
    manager = get_skills_manager()
    skill = manager.get_skill(skill_id)
    
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
    
    skill.enabled = enabled
    manager.add_skill(skill)
    
    return {"success": True, "skill_id": skill_id, "enabled": enabled}


# ==================== MCP Servers API ====================

@router.get("/mcp")
async def list_mcp_servers() -> Dict[str, Any]:
    """获取 MCP 服务器列表"""
    return {"servers": _mcp_servers, "total": len(_mcp_servers)}


@router.post("/mcp")
async def add_mcp_server(server: MCPServerCreate) -> Dict[str, Any]:
    """添加 MCP 服务器"""
    # 检查是否已存在
    for s in _mcp_servers:
        if s.get("name") == server.name:
            raise HTTPException(status_code=400, detail=f"Server already exists: {server.name}")
    
    _mcp_servers.append({
        "name": server.name,
        "type": server.server_type,
        "url": server.url,
        "config": server.config or {},
        "status": "unknown",
    })
    
    return {"success": True, "name": server.name, "message": "MCP 服务器已添加"}


@router.delete("/mcp/{server_name}")
async def remove_mcp_server(server_name: str) -> Dict[str, Any]:
    """删除 MCP 服务器"""
    global _mcp_servers
    
    original_len = len(_mcp_servers)
    _mcp_servers = [s for s in _mcp_servers if s.get("name") != server_name]
    
    if len(_mcp_servers) < original_len:
        return {"success": True, "message": "MCP 服务器已删除"}
    else:
        raise HTTPException(status_code=404, detail=f"Server not found: {server_name}")


# ==================== Summary API ====================

@router.get("/summary")
async def get_settings_summary(workspace: str = ".") -> Dict[str, Any]:
    """获取设置摘要"""
    try:
        indexer = get_workspace_indexer(workspace)
        indexed_files = indexer.get_indexed_files()
        
        manager = get_skills_manager()
        skills = manager.list_skills()
        
        return {
            "indexed_files": len(indexed_files),
            "user_rules": len(_rules_store["user_rules"]),
            "project_rules": len(_rules_store["project_rules"]),
            "skills": len(skills),
            "mcp_servers": len(_mcp_servers),
        }
    except Exception as e:
        logger.error(f"Get settings summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))






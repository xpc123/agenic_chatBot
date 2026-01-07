# -*- coding: utf-8 -*-
"""
Settings UI - Cursor 风格设置界面

提供类似 Cursor 的设置界面：
1. Indexing & Docs - 索引与文档管理
2. Rules & Commands - 规则与命令
3. Tools & MCP - 工具与 MCP 服务器
"""
import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# 获取项目根目录
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# 添加 backend 路径
sys.path.insert(0, str(PROJECT_ROOT / 'backend'))

import gradio as gr
from loguru import logger

# 导入核心组件
from app.rag.workspace_indexer import WorkspaceIndexer, get_workspace_indexer, IndexingStatus
from app.core.skills import SkillsManager, Skill


# ==================== 配置管理 ====================

class SettingsManager:
    """设置管理器"""
    
    def __init__(self, workspace_path: str = None):
        self.workspace_path = Path(workspace_path or PROJECT_ROOT)
        self.config_path = self.workspace_path / '.agentic_chatbot' / 'settings.json'
        self.cursorignore_path = self.workspace_path / '.cursorignore'
        self.readme_path = self.workspace_path / 'README.md'
        
        # 默认设置
        self.default_settings = {
            "indexing": {
                "enabled": True,
                "auto_index_new_folders": True,
                "max_folder_size": 250000,
                "ignore_patterns": []
            },
            "rules": {
                "include_readme_in_context": True,
                "user_rules": [],
                "project_rules": []
            },
            "commands": {
                "user_commands": [],
                "project_commands": []
            },
            "tools": {
                "browser_automation": False,
                "show_localhost_links": True,
                "mcp_servers": []
            },
            "docs": []
        }
        
        self.settings = self._load_settings()
    
    def _load_settings(self) -> Dict[str, Any]:
        """加载设置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # 合并默认设置
                    return {**self.default_settings, **loaded}
            except Exception as e:
                logger.warning(f"Failed to load settings: {e}")
        return self.default_settings.copy()
    
    def save_settings(self):
        """保存设置"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            logger.info("Settings saved")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
    
    def get_ignore_patterns(self) -> List[str]:
        """获取忽略模式"""
        patterns = list(self.settings["indexing"]["ignore_patterns"])
        
        # 从 .cursorignore 加载
        if self.cursorignore_path.exists():
            try:
                with open(self.cursorignore_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            patterns.append(line)
            except Exception:
                pass
        
        return patterns
    
    def save_ignore_patterns(self, patterns: List[str]):
        """保存忽略模式到 .cursorignore"""
        try:
            with open(self.cursorignore_path, 'w', encoding='utf-8') as f:
                f.write("# Agentic ChatBot Ignore Patterns\n")
                f.write("# 这些文件/目录将被排除在索引之外\n\n")
                for pattern in patterns:
                    if pattern.strip():
                        f.write(f"{pattern}\n")
            logger.info(f"Saved {len(patterns)} ignore patterns")
        except Exception as e:
            logger.error(f"Failed to save ignore patterns: {e}")
    
    def get_readme_content(self) -> str:
        """获取 README 内容"""
        if self.readme_path.exists():
            try:
                with open(self.readme_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception:
                pass
        return ""
    
    def add_user_rule(self, rule: str):
        """添加用户规则"""
        if rule and rule not in self.settings["rules"]["user_rules"]:
            self.settings["rules"]["user_rules"].append(rule)
            self.save_settings()
    
    def remove_user_rule(self, rule: str):
        """删除用户规则"""
        if rule in self.settings["rules"]["user_rules"]:
            self.settings["rules"]["user_rules"].remove(rule)
            self.save_settings()
    
    def add_project_rule(self, rule: str):
        """添加项目规则"""
        if rule and rule not in self.settings["rules"]["project_rules"]:
            self.settings["rules"]["project_rules"].append(rule)
            self.save_settings()
    
    def add_mcp_server(self, name: str, config: Dict):
        """添加 MCP 服务器"""
        server = {"name": name, **config}
        self.settings["tools"]["mcp_servers"].append(server)
        self.save_settings()
    
    def remove_mcp_server(self, name: str):
        """删除 MCP 服务器"""
        self.settings["tools"]["mcp_servers"] = [
            s for s in self.settings["tools"]["mcp_servers"] 
            if s.get("name") != name
        ]
        self.save_settings()
    
    def add_doc(self, doc_path: str):
        """添加文档"""
        if doc_path and doc_path not in self.settings["docs"]:
            self.settings["docs"].append(doc_path)
            self.save_settings()
    
    def remove_doc(self, doc_path: str):
        """删除文档"""
        if doc_path in self.settings["docs"]:
            self.settings["docs"].remove(doc_path)
            self.save_settings()


# ==================== 全局状态 ====================

settings_manager = SettingsManager(str(PROJECT_ROOT))
workspace_indexer: Optional[WorkspaceIndexer] = None
skills_manager: Optional[SkillsManager] = None


def get_skills_manager() -> SkillsManager:
    """获取 Skills 管理器"""
    global skills_manager
    if skills_manager is None:
        skills_manager = SkillsManager()
    return skills_manager


def get_indexer() -> WorkspaceIndexer:
    """获取索引器"""
    global workspace_indexer
    if workspace_indexer is None:
        workspace_indexer = get_workspace_indexer(str(PROJECT_ROOT))
    return workspace_indexer


# ==================== UI 回调函数 ====================

def get_indexing_status() -> Tuple[str, str, str]:
    """获取索引状态"""
    try:
        indexer = get_indexer()
        status = indexer.get_status()
        indexed_files = indexer.get_indexed_files()
        
        # 计算进度
        if status.total_files > 0:
            progress = int((status.indexed_files / status.total_files) * 100)
        else:
            progress = 100 if status.is_complete else 0
        
        # 状态文本
        if status.is_complete:
            status_text = f"✅ 索引完成"
        elif status.current_file:
            status_text = f"🔄 正在索引: {status.current_file}"
        else:
            status_text = "⏳ 等待索引"
        
        # 统计信息
        stats = f"""
### 📊 索引统计

| 项目 | 数量 |
|------|------|
| **已索引文件** | {len(indexed_files)} |
| **本次索引** | {status.indexed_files} |
| **跳过文件** | {status.skipped_files} |
| **失败文件** | {status.failed_files} |
| **进度** | {progress}% |
"""
        
        return status_text, f"{progress}%", stats
        
    except Exception as e:
        return f"❌ 错误: {e}", "0%", ""


def trigger_sync():
    """触发同步"""
    try:
        import asyncio
        indexer = get_indexer()
        
        # 运行索引
        loop = asyncio.new_event_loop()
        status = loop.run_until_complete(
            indexer.index_workspace(force=False, priority_only=False)
        )
        loop.close()
        
        return f"✅ 同步完成！索引了 {status.indexed_files} 个文件"
    except Exception as e:
        return f"❌ 同步失败: {e}"


def delete_index():
    """删除索引"""
    try:
        indexer = get_indexer()
        indexer.clear_index()
        return "✅ 索引已删除"
    except Exception as e:
        return f"❌ 删除失败: {e}"


def get_indexed_files_list() -> str:
    """获取已索引文件列表"""
    try:
        indexer = get_indexer()
        files = indexer.get_indexed_files()
        
        if not files:
            return "暂无已索引文件"
        
        # 分类显示
        md_files = [f for f in files if f.endswith('.md')]
        py_files = [f for f in files if f.endswith('.py')]
        other_files = [f for f in files if not f.endswith('.md') and not f.endswith('.py')]
        
        result = "### 📁 已索引文件\n\n"
        
        if md_files:
            result += "**📝 Markdown 文件:**\n"
            for f in md_files[:20]:
                result += f"- {f}\n"
            if len(md_files) > 20:
                result += f"- ... 还有 {len(md_files) - 20} 个\n"
            result += "\n"
        
        if py_files:
            result += "**🐍 Python 文件:**\n"
            for f in py_files[:20]:
                result += f"- {f}\n"
            if len(py_files) > 20:
                result += f"- ... 还有 {len(py_files) - 20} 个\n"
            result += "\n"
        
        if other_files:
            result += "**📄 其他文件:**\n"
            for f in other_files[:10]:
                result += f"- {f}\n"
            if len(other_files) > 10:
                result += f"- ... 还有 {len(other_files) - 10} 个\n"
        
        result += f"\n**总计: {len(files)} 个文件**"
        return result
        
    except Exception as e:
        return f"❌ 获取失败: {e}"


def get_ignore_patterns() -> str:
    """获取忽略模式"""
    patterns = settings_manager.get_ignore_patterns()
    return "\n".join(patterns)


def save_ignore_patterns(patterns_text: str) -> str:
    """保存忽略模式"""
    patterns = [p.strip() for p in patterns_text.split("\n") if p.strip()]
    settings_manager.save_ignore_patterns(patterns)
    return f"✅ 已保存 {len(patterns)} 条规则"


def get_user_rules() -> str:
    """获取用户规则"""
    rules = settings_manager.settings["rules"]["user_rules"]
    if not rules:
        return "暂无用户规则"
    return "\n".join([f"• {r}" for r in rules])


def add_user_rule(rule: str) -> Tuple[str, str]:
    """添加用户规则"""
    if not rule.strip():
        return get_user_rules(), "请输入规则内容"
    settings_manager.add_user_rule(rule.strip())
    return get_user_rules(), f"✅ 已添加规则"


def get_project_rules() -> str:
    """获取项目规则"""
    rules = settings_manager.settings["rules"]["project_rules"]
    if not rules:
        return "暂无项目规则"
    return "\n".join([f"• {r}" for r in rules])


def add_project_rule(rule: str) -> Tuple[str, str]:
    """添加项目规则"""
    if not rule.strip():
        return get_project_rules(), "请输入规则内容"
    settings_manager.add_project_rule(rule.strip())
    return get_project_rules(), f"✅ 已添加规则"


def get_mcp_servers() -> str:
    """获取 MCP 服务器列表"""
    servers = settings_manager.settings["tools"]["mcp_servers"]
    if not servers:
        return "### 暂无 MCP 服务器\n\n点击 'Add Custom MCP' 添加自定义 MCP 工具"
    
    result = "### 🔌 已安装 MCP 服务器\n\n"
    for server in servers:
        result += f"**{server.get('name', 'Unknown')}**\n"
        result += f"- 类型: {server.get('type', 'unknown')}\n"
        if server.get('url'):
            result += f"- URL: {server.get('url')}\n"
        result += "\n"
    
    return result


def add_mcp_server(name: str, server_type: str, url: str) -> Tuple[str, str]:
    """添加 MCP 服务器"""
    if not name.strip():
        return get_mcp_servers(), "请输入服务器名称"
    
    config = {
        "type": server_type,
        "url": url.strip() if url else None
    }
    settings_manager.add_mcp_server(name.strip(), config)
    return get_mcp_servers(), f"✅ 已添加 MCP 服务器: {name}"


def get_docs_list() -> str:
    """获取文档列表"""
    docs = settings_manager.settings["docs"]
    if not docs:
        return "### 暂无添加的文档\n\n添加文档以用作上下文。您也可以在聊天中使用 @Add 添加文档。"
    
    result = "### 📚 已添加的文档\n\n"
    for doc in docs:
        result += f"- {doc}\n"
    return result


def add_doc(doc_path: str) -> Tuple[str, str]:
    """添加文档"""
    if not doc_path.strip():
        return get_docs_list(), "请输入文档路径"
    settings_manager.add_doc(doc_path.strip())
    return get_docs_list(), f"✅ 已添加文档: {doc_path}"


def toggle_readme_context(enabled: bool) -> str:
    """切换 README 上下文"""
    settings_manager.settings["rules"]["include_readme_in_context"] = enabled
    settings_manager.save_settings()
    return f"README 上下文: {'已启用' if enabled else '已禁用'}"


def toggle_auto_index(enabled: bool) -> str:
    """切换自动索引"""
    settings_manager.settings["indexing"]["auto_index_new_folders"] = enabled
    settings_manager.save_settings()
    return f"自动索引新文件夹: {'已启用' if enabled else '已禁用'}"


def toggle_browser_automation(enabled: bool) -> str:
    """切换浏览器自动化"""
    settings_manager.settings["tools"]["browser_automation"] = enabled
    settings_manager.save_settings()
    return f"浏览器自动化: {'已启用' if enabled else '已禁用'}"


# ==================== Skills 管理函数 ====================

def get_skills_list() -> str:
    """获取 Skills 列表"""
    try:
        manager = get_skills_manager()
        skills = manager.list_skills()
        
        if not skills:
            return "### 暂无技能\n\n点击 '创建新技能' 添加自定义技能"
        
        result = "### 🎯 已安装技能\n\n"
        
        # 按分类分组
        categories: Dict[str, list] = {}
        for skill in skills:
            cat = skill.category or "general"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(skill)
        
        for cat, cat_skills in categories.items():
            result += f"**📂 {cat.upper()}**\n\n"
            for skill in cat_skills:
                status = "✅" if skill.enabled else "☐"
                triggers = ", ".join(skill.triggers[:3]) if skill.triggers else "无"
                result += f"{status} **{skill.name}** (`{skill.id}`)\n"
                result += f"   触发词: {triggers}\n\n"
        
        result += f"\n**总计: {len(skills)} 个技能**"
        return result
        
    except Exception as e:
        return f"❌ 获取技能失败: {e}"


def get_skill_details(skill_id: str) -> Tuple[str, str, str, str, bool]:
    """获取技能详情"""
    try:
        if not skill_id:
            return "", "", "", "", True
        
        manager = get_skills_manager()
        skill = manager.get_skill(skill_id)
        
        if not skill:
            return "", "", "", "", True
        
        triggers = ", ".join(skill.triggers) if skill.triggers else ""
        return skill.name, skill.description, skill.instructions, triggers, skill.enabled
        
    except Exception as e:
        logger.error(f"Failed to get skill details: {e}")
        return "", "", "", "", True


def toggle_skill(skill_id: str, enabled: bool) -> Tuple[str, str]:
    """启用/禁用技能"""
    try:
        if not skill_id:
            return get_skills_list(), "请先选择一个技能"
        
        manager = get_skills_manager()
        skill = manager.get_skill(skill_id)
        
        if skill:
            skill.enabled = enabled
            manager.add_skill(skill)  # add_skill 会更新已存在的技能
            status = "已启用" if enabled else "已禁用"
            return get_skills_list(), f"✅ 技能 '{skill.name}' {status}"
        
        return get_skills_list(), "❌ 技能不存在"
        
    except Exception as e:
        return get_skills_list(), f"❌ 操作失败: {e}"


def save_skill(
    skill_id: str,
    name: str,
    description: str,
    instructions: str,
    triggers: str,
    enabled: bool
) -> Tuple[str, str]:
    """保存技能"""
    try:
        if not skill_id or not name:
            return get_skills_list(), "请输入技能 ID 和名称"
        
        manager = get_skills_manager()
        
        # 解析触发词
        trigger_list = [t.strip() for t in triggers.split(",") if t.strip()]
        
        # 获取现有技能以保留 category
        existing = manager.get_skill(skill_id)
        category = existing.category if existing else "custom"
        
        skill = Skill(
            id=skill_id,
            name=name,
            description=description,
            instructions=instructions,
            triggers=trigger_list,
            category=category,
            enabled=enabled
        )
        
        manager.add_skill(skill)  # add_skill 会更新已存在的技能
        return get_skills_list(), f"✅ 技能 '{name}' 已保存"
        
    except Exception as e:
        return get_skills_list(), f"❌ 保存失败: {e}"


def create_new_skill(
    skill_id: str,
    name: str,
    description: str,
    instructions: str,
    triggers: str,
    category: str
) -> Tuple[str, str]:
    """创建新技能"""
    try:
        if not skill_id or not name:
            return get_skills_list(), "请输入技能 ID 和名称"
        
        manager = get_skills_manager()
        
        # 检查是否已存在
        if manager.get_skill(skill_id):
            return get_skills_list(), f"❌ 技能 ID '{skill_id}' 已存在"
        
        # 解析触发词
        trigger_list = [t.strip() for t in triggers.split(",") if t.strip()]
        
        skill = Skill(
            id=skill_id,
            name=name,
            description=description,
            instructions=instructions,
            triggers=trigger_list,
            category=category or "custom",
            enabled=True
        )
        
        manager.add_skill(skill)
        return get_skills_list(), f"✅ 技能 '{name}' 已创建"
        
    except Exception as e:
        return get_skills_list(), f"❌ 创建失败: {e}"


def delete_skill(skill_id: str) -> Tuple[str, str]:
    """删除技能"""
    try:
        if not skill_id:
            return get_skills_list(), "请先选择一个技能"
        
        manager = get_skills_manager()
        
        # 检查是否为内置技能
        builtin_ids = [
            "code_review", "write_docs", "data_analysis", "debug_helper",
            "virtuoso_skill", "shell_expert", "python_expert", "system_admin", "api_designer"
        ]
        if skill_id in builtin_ids:
            return get_skills_list(), "❌ 无法删除内置技能"
        
        manager.remove_skill(skill_id)
        return get_skills_list(), f"✅ 技能 '{skill_id}' 已删除"
        
    except Exception as e:
        return get_skills_list(), f"❌ 删除失败: {e}"


def get_skill_choices() -> List[Tuple[str, str]]:
    """获取技能选项列表"""
    try:
        manager = get_skills_manager()
        skills = manager.list_skills()
        return [(f"{s.name} ({s.id})", s.id) for s in skills]
    except Exception:
        return []


# ==================== 创建 UI ====================

def create_settings_ui() -> gr.Blocks:
    """创建设置界面"""
    
    with gr.Blocks(
        title="Agentic ChatBot Settings",
    ) as app:
        
        gr.Markdown("# ⚙️ Agentic ChatBot Settings")
        gr.Markdown("*类似 Cursor 的设置界面*")
        
        with gr.Tabs():
            
            # ==================== Indexing & Docs ====================
            with gr.TabItem("📁 Indexing & Docs"):
                
                gr.Markdown("## Codebase Indexing")
                gr.Markdown("*嵌入代码库以获得更好的上下文理解和知识*")
                
                with gr.Row():
                    with gr.Column(scale=3):
                        indexing_status = gr.Textbox(
                            label="状态",
                            value="加载中...",
                            interactive=False
                        )
                        indexing_progress = gr.Textbox(
                            label="进度",
                            value="0%",
                            interactive=False
                        )
                    with gr.Column(scale=1):
                        sync_btn = gr.Button("🔄 Sync", variant="secondary")
                        delete_btn = gr.Button("🗑️ Delete Index", variant="stop")
                
                sync_result = gr.Textbox(label="操作结果", visible=True)
                
                indexing_stats = gr.Markdown("加载中...")
                
                gr.Markdown("---")
                
                # 自动索引开关
                with gr.Row():
                    auto_index_toggle = gr.Checkbox(
                        label="Index New Folders",
                        info="自动索引少于 250,000 个文件的新文件夹",
                        value=settings_manager.settings["indexing"]["auto_index_new_folders"]
                    )
                
                gr.Markdown("---")
                
                # 忽略文件配置
                gr.Markdown("### Ignore Files in .cursorignore")
                gr.Markdown("*除 .gitignore 外，需要从索引中排除的文件*")
                
                ignore_patterns = gr.Textbox(
                    label="忽略规则（每行一个）",
                    value=get_ignore_patterns(),
                    lines=8,
                    placeholder="node_modules/\nvenv/\n*.log"
                )
                save_ignore_btn = gr.Button("💾 保存忽略规则")
                ignore_result = gr.Textbox(label="", visible=True)
                
                with gr.Accordion("📋 View included files", open=False):
                    indexed_files_list = gr.Markdown(get_indexed_files_list())
                    refresh_files_btn = gr.Button("🔄 刷新列表")
                
                gr.Markdown("---")
                
                # 文档管理
                gr.Markdown("### Docs")
                gr.Markdown("*添加自定义资源和开发者文档*")
                
                docs_list = gr.Markdown(get_docs_list())
                
                with gr.Row():
                    doc_path_input = gr.Textbox(
                        label="文档路径",
                        placeholder="./docs/api.md"
                    )
                    add_doc_btn = gr.Button("➕ Add Doc", variant="primary")
                
                doc_result = gr.Textbox(label="", visible=True)
            
            # ==================== Rules and Commands ====================
            with gr.TabItem("📜 Rules and Commands"):
                
                gr.Markdown("## Import Settings")
                
                with gr.Row():
                    readme_toggle = gr.Checkbox(
                        label="Include README.md in context",
                        info="README.md 文件将在相关时添加到 Agent 的上下文中",
                        value=settings_manager.settings["rules"]["include_readme_in_context"]
                    )
                
                gr.Markdown("---")
                
                # 用户规则
                gr.Markdown("### User Rules")
                gr.Markdown("*管理您的自定义用户规则和偏好*")
                
                user_rules_display = gr.Markdown(get_user_rules())
                
                with gr.Row():
                    user_rule_input = gr.Textbox(
                        label="新规则",
                        placeholder="例如：始终使用中文回复"
                    )
                    add_user_rule_btn = gr.Button("➕ Add Rule", variant="primary")
                
                user_rule_result = gr.Textbox(label="", visible=True)
                
                gr.Markdown("---")
                
                # 项目规则
                gr.Markdown("### Project Rules")
                gr.Markdown("*帮助 Agent 理解此项目目录中的约定*")
                
                project_rules_display = gr.Markdown(get_project_rules())
                
                with gr.Row():
                    project_rule_input = gr.Textbox(
                        label="新规则",
                        placeholder="例如：使用 FastAPI 风格的路由"
                    )
                    add_project_rule_btn = gr.Button("➕ Add Rule", variant="primary")
                
                project_rule_result = gr.Textbox(label="", visible=True)
                
                gr.Markdown("---")
                
                # 命令（简化版）
                gr.Markdown("### Commands")
                gr.Markdown("*命令功能即将推出...*")
            
            # ==================== Skills ====================
            with gr.TabItem("🎯 Skills"):
                
                gr.Markdown("## 技能管理")
                gr.Markdown("*类似 Anthropic Skills，管理 AI 的专业能力*")
                
                with gr.Row():
                    # 左侧：技能列表
                    with gr.Column(scale=1):
                        skills_list_display = gr.Markdown(get_skills_list())
                        
                        gr.Markdown("---")
                        
                        skill_selector = gr.Dropdown(
                            label="选择技能",
                            choices=[],
                            interactive=True
                        )
                        
                        with gr.Row():
                            refresh_skills_btn = gr.Button("🔄 刷新", size="sm")
                            delete_skill_btn = gr.Button("🗑️ 删除", variant="stop", size="sm")
                    
                    # 右侧：技能详情/编辑
                    with gr.Column(scale=2):
                        gr.Markdown("### 📝 技能详情")
                        
                        skill_id_input = gr.Textbox(
                            label="技能 ID",
                            placeholder="my_custom_skill",
                            interactive=True
                        )
                        
                        skill_name_input = gr.Textbox(
                            label="技能名称",
                            placeholder="我的自定义技能"
                        )
                        
                        skill_desc_input = gr.Textbox(
                            label="描述",
                            placeholder="这个技能用于..."
                        )
                        
                        skill_instructions_input = gr.Textbox(
                            label="指令 (System Prompt 扩展)",
                            placeholder="作为专家，请按以下步骤处理...",
                            lines=8
                        )
                        
                        skill_triggers_input = gr.Textbox(
                            label="触发词 (逗号分隔)",
                            placeholder="关键词1, 关键词2, 关键词3"
                        )
                        
                        skill_enabled_toggle = gr.Checkbox(
                            label="启用此技能",
                            value=True
                        )
                        
                        with gr.Row():
                            save_skill_btn = gr.Button("💾 保存修改", variant="primary")
                            create_skill_btn = gr.Button("➕ 创建新技能", variant="secondary")
                        
                        skill_result = gr.Textbox(label="操作结果", visible=True)
                
                gr.Markdown("---")
                
                with gr.Accordion("💡 如何使用 Skills", open=False):
                    gr.Markdown("""
### Skills 工作原理

1. **触发词匹配**: 当用户消息包含触发词时，自动激活对应技能
2. **指令注入**: 技能的指令会被添加到 System Prompt 中
3. **专业能力**: 每个技能代表一种专业能力（代码审查、调试、文档撰写等）

### 内置技能

| 技能 | 触发词 | 用途 |
|------|--------|------|
| code_review | 审查, review | 代码审查 |
| write_docs | 写文档, documentation | 文档撰写 |
| debug_helper | 报错, error, debug | 调试帮助 |
| data_analysis | 分析数据, analyze | 数据分析 |

### 创建自定义技能

1. 填写技能 ID（唯一标识，英文）
2. 填写名称和描述
3. 编写详细的指令（告诉 AI 如何处理）
4. 设置触发词（用户消息包含这些词时激活）
5. 点击 "创建新技能"
                    """)
            
            # ==================== Tools & MCP ====================
            with gr.TabItem("🔧 Tools & MCP"):
                
                gr.Markdown("## Tools")
                
                # 浏览器自动化
                gr.Markdown("### Browser")
                
                browser_toggle = gr.Checkbox(
                    label="Browser Automation",
                    info="启用浏览器自动化功能",
                    value=settings_manager.settings["tools"]["browser_automation"]
                )
                
                localhost_toggle = gr.Checkbox(
                    label="Show Localhost Links in Browser",
                    info="自动在浏览器标签中打开 localhost 链接",
                    value=settings_manager.settings["tools"]["show_localhost_links"]
                )
                
                gr.Markdown("---")
                
                # MCP 服务器
                gr.Markdown("### Installed MCP Servers")
                
                mcp_servers_display = gr.Markdown(get_mcp_servers())
                
                gr.Markdown("*添加自定义 MCP 工具或在 `<project-root>/.cursor/mcp.json` 中配置项目特定的工具*")
                
                with gr.Row():
                    mcp_name_input = gr.Textbox(label="服务器名称", placeholder="my-mcp-server")
                    mcp_type_input = gr.Dropdown(
                        label="类型",
                        choices=["http", "sqlite", "custom"],
                        value="http"
                    )
                    mcp_url_input = gr.Textbox(label="URL", placeholder="http://localhost:9000")
                
                add_mcp_btn = gr.Button("➕ Add Custom MCP", variant="primary")
                mcp_result = gr.Textbox(label="", visible=True)
        
        # ==================== 事件绑定 ====================
        
        # 页面加载时获取索引状态
        app.load(
            get_indexing_status,
            outputs=[indexing_status, indexing_progress, indexing_stats]
        )
        
        # Sync 按钮
        sync_btn.click(
            trigger_sync,
            outputs=[sync_result]
        ).then(
            get_indexing_status,
            outputs=[indexing_status, indexing_progress, indexing_stats]
        )
        
        # Delete Index 按钮
        delete_btn.click(
            delete_index,
            outputs=[sync_result]
        ).then(
            get_indexing_status,
            outputs=[indexing_status, indexing_progress, indexing_stats]
        )
        
        # 自动索引开关
        auto_index_toggle.change(
            toggle_auto_index,
            inputs=[auto_index_toggle],
            outputs=[sync_result]
        )
        
        # 保存忽略规则
        save_ignore_btn.click(
            save_ignore_patterns,
            inputs=[ignore_patterns],
            outputs=[ignore_result]
        )
        
        # 刷新文件列表
        refresh_files_btn.click(
            get_indexed_files_list,
            outputs=[indexed_files_list]
        )
        
        # 添加文档
        add_doc_btn.click(
            add_doc,
            inputs=[doc_path_input],
            outputs=[docs_list, doc_result]
        )
        
        # README 开关
        readme_toggle.change(
            toggle_readme_context,
            inputs=[readme_toggle],
            outputs=[user_rule_result]
        )
        
        # 添加用户规则
        add_user_rule_btn.click(
            add_user_rule,
            inputs=[user_rule_input],
            outputs=[user_rules_display, user_rule_result]
        )
        
        # 添加项目规则
        add_project_rule_btn.click(
            add_project_rule,
            inputs=[project_rule_input],
            outputs=[project_rules_display, project_rule_result]
        )
        
        # 浏览器自动化开关
        browser_toggle.change(
            toggle_browser_automation,
            inputs=[browser_toggle],
            outputs=[mcp_result]
        )
        
        # 添加 MCP 服务器
        add_mcp_btn.click(
            add_mcp_server,
            inputs=[mcp_name_input, mcp_type_input, mcp_url_input],
            outputs=[mcp_servers_display, mcp_result]
        )
        
        # ==================== Skills 事件绑定 ====================
        
        def update_skill_selector():
            """更新技能选择器"""
            choices = get_skill_choices()
            return gr.Dropdown(choices=choices)
        
        def on_skill_selected(selected):
            """选择技能时加载详情"""
            if not selected:
                return "", "", "", "", True
            return get_skill_details(selected)
        
        # 页面加载时更新技能选择器
        app.load(
            update_skill_selector,
            outputs=[skill_selector]
        )
        
        # 选择技能时加载详情
        skill_selector.change(
            on_skill_selected,
            inputs=[skill_selector],
            outputs=[skill_name_input, skill_desc_input, skill_instructions_input, 
                     skill_triggers_input, skill_enabled_toggle]
        ).then(
            lambda x: x if x else "",
            inputs=[skill_selector],
            outputs=[skill_id_input]
        )
        
        # 刷新技能列表
        refresh_skills_btn.click(
            get_skills_list,
            outputs=[skills_list_display]
        ).then(
            update_skill_selector,
            outputs=[skill_selector]
        )
        
        # 保存技能
        save_skill_btn.click(
            save_skill,
            inputs=[skill_id_input, skill_name_input, skill_desc_input,
                    skill_instructions_input, skill_triggers_input, skill_enabled_toggle],
            outputs=[skills_list_display, skill_result]
        ).then(
            update_skill_selector,
            outputs=[skill_selector]
        )
        
        # 创建新技能
        create_skill_btn.click(
            lambda id, name, desc, instr, triggers: create_new_skill(
                id, name, desc, instr, triggers, "custom"
            ),
            inputs=[skill_id_input, skill_name_input, skill_desc_input,
                    skill_instructions_input, skill_triggers_input],
            outputs=[skills_list_display, skill_result]
        ).then(
            update_skill_selector,
            outputs=[skill_selector]
        )
        
        # 删除技能
        delete_skill_btn.click(
            delete_skill,
            inputs=[skill_id_input],
            outputs=[skills_list_display, skill_result]
        ).then(
            update_skill_selector,
            outputs=[skill_selector]
        ).then(
            lambda: ("", "", "", "", True),
            outputs=[skill_name_input, skill_desc_input, skill_instructions_input,
                     skill_triggers_input, skill_enabled_toggle]
        )
    
    return app


def launch_settings_ui(host: str = "0.0.0.0", port: int = 7863):
    """启动设置界面"""
    app = create_settings_ui()
    
    print("""
╔════════════════════════════════════════════════════════════════╗
║         ⚙️ Agentic ChatBot Settings - Cursor Style             ║
╠════════════════════════════════════════════════════════════════╣
║  📁 Indexing & Docs | 📜 Rules & Commands | 🔧 Tools & MCP     ║
║  📍 启动后访问: http://localhost:{port}                          ║
╚════════════════════════════════════════════════════════════════╝
    """.format(port=port))
    
    app.launch(
        server_name=host,
        server_port=port,
        share=False,
        theme=gr.themes.Soft()
    )


if __name__ == "__main__":
    launch_settings_ui()


# -*- coding: utf-8 -*-
"""
Skills 系统 - 可复用的任务能力

类似 Anthropic Skills，支持：
- 自定义任务指令
- 可保存和复用
- 动态加载
- 示例和模板
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict
from loguru import logger

from ..config import settings


# ==================== 数据模型 ====================

@dataclass
class Skill:
    """
    技能定义
    
    一个 Skill 包含完成特定任务所需的所有信息
    """
    id: str                                    # 唯一标识
    name: str                                  # 技能名称
    description: str                           # 技能描述
    instructions: str                          # 详细指令（System Prompt 扩展）
    examples: List[Dict[str, str]] = field(default_factory=list)  # 示例对话
    templates: Dict[str, str] = field(default_factory=dict)       # 输出模板
    triggers: List[str] = field(default_factory=list)             # 触发关键词
    category: str = "general"                  # 分类
    enabled: bool = True                       # 是否启用
    created_at: str = ""                       # 创建时间
    updated_at: str = ""                       # 更新时间
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Skill":
        return cls(**data)
    
    def matches(self, query: str) -> bool:
        """检查查询是否匹配此技能的触发条件"""
        query_lower = query.lower()
        for trigger in self.triggers:
            if trigger.lower() in query_lower:
                return True
        return False
    
    def get_prompt_extension(self) -> str:
        """获取添加到 System Prompt 的扩展内容"""
        parts = [
            f"## 技能: {self.name}",
            f"描述: {self.description}",
            "",
            "### 指令",
            self.instructions,
        ]
        
        if self.examples:
            parts.append("")
            parts.append("### 示例")
            for i, ex in enumerate(self.examples, 1):
                parts.append(f"**示例 {i}:**")
                parts.append(f"用户: {ex.get('user', '')}")
                parts.append(f"助手: {ex.get('assistant', '')}")
        
        if self.templates:
            parts.append("")
            parts.append("### 输出模板")
            for name, template in self.templates.items():
                parts.append(f"**{name}:**")
                parts.append(f"```\n{template}\n```")
        
        return "\n".join(parts)


# ==================== Skills 管理器 ====================

class SkillsManager:
    """
    技能管理器
    
    职责:
    1. 加载/保存技能
    2. 根据查询匹配技能
    3. 生成技能增强的 Prompt
    """
    
    def __init__(self, skills_dir: Optional[str] = None):
        self.skills_dir = Path(skills_dir) if skills_dir else Path(settings.DATA_DIR) / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        
        self.skills: Dict[str, Skill] = {}
        self._load_skills()
        self._load_builtin_skills()
        
        logger.info(f"SkillsManager initialized with {len(self.skills)} skills")
    
    def _load_skills(self):
        """从磁盘加载技能"""
        skills_file = self.skills_dir / "skills.json"
        
        if skills_file.exists():
            try:
                with open(skills_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for skill_data in data.get("skills", []):
                        skill = Skill.from_dict(skill_data)
                        self.skills[skill.id] = skill
                logger.info(f"Loaded {len(self.skills)} skills from disk")
            except Exception as e:
                logger.error(f"Failed to load skills: {e}")
    
    def _load_builtin_skills(self):
        """加载内置技能"""
        builtin = [
            Skill(
                id="code_review",
                name="代码审查",
                description="按照最佳实践审查代码",
                instructions="""
作为代码审查专家，请按以下步骤审查代码：

1. **正确性**: 代码逻辑是否正确？
2. **可读性**: 命名是否清晰？注释是否足够？
3. **性能**: 是否有性能问题？
4. **安全性**: 是否有安全漏洞？
5. **最佳实践**: 是否遵循语言/框架的最佳实践？

给出具体的改进建议，并提供修改后的代码示例。
                """,
                examples=[
                    {
                        "user": "帮我审查这段代码：def add(a,b): return a+b",
                        "assistant": "## 代码审查结果\n\n**正确性**: ✅ 逻辑正确\n**可读性**: ⚠️ 建议添加类型注解和文档字符串\n\n**建议改进**:\n```python\ndef add(a: int, b: int) -> int:\n    \"\"\"计算两数之和\"\"\"\n    return a + b\n```"
                    }
                ],
                triggers=["审查", "review", "检查代码", "code review"],
                category="development",
            ),
            Skill(
                id="write_docs",
                name="文档撰写",
                description="撰写清晰、专业的技术文档",
                instructions="""
作为技术文档专家，请遵循以下原则：

1. **结构清晰**: 使用标题、列表、代码块组织内容
2. **简洁明了**: 避免冗长，每段话聚焦一个要点
3. **示例丰富**: 提供代码示例和使用场景
4. **用户导向**: 从用户角度出发，解答"为什么"和"怎么做"

输出格式:
- 使用 Markdown
- 包含目录（如果内容较长）
- 代码块标注语言
                """,
                triggers=["写文档", "文档", "documentation", "readme", "说明"],
                category="writing",
            ),
            Skill(
                id="data_analysis",
                name="数据分析",
                description="分析数据并提供洞察",
                instructions="""
作为数据分析师，请按以下流程分析：

1. **数据概览**: 描述数据的基本特征（大小、类型、缺失值）
2. **统计分析**: 计算关键统计指标
3. **可视化建议**: 推荐合适的图表类型
4. **洞察发现**: 提炼关键发现和模式
5. **建议行动**: 基于分析给出建议

使用 Python 代码进行分析，使用 pandas、numpy 等库。
                """,
                triggers=["分析数据", "数据分析", "analyze", "统计"],
                category="analytics",
            ),
            Skill(
                id="debug_helper",
                name="调试助手",
                description="帮助定位和解决代码问题",
                instructions="""
作为调试专家，请按以下步骤帮助解决问题：

1. **理解错误**: 解释错误信息的含义
2. **定位原因**: 分析可能的原因
3. **提供解决方案**: 给出具体的修复代码
4. **预防建议**: 如何避免类似问题

如果需要更多信息，请明确询问：
- 完整的错误堆栈
- 相关代码
- 运行环境
                """,
                triggers=["报错", "错误", "error", "debug", "bug", "不工作", "失败"],
                category="development",
            ),
        ]
        
        for skill in builtin:
            if skill.id not in self.skills:
                self.skills[skill.id] = skill
    
    def _save_skills(self):
        """保存技能到磁盘"""
        skills_file = self.skills_dir / "skills.json"
        
        try:
            data = {
                "skills": [s.to_dict() for s in self.skills.values() if s.id not in ["code_review", "write_docs", "data_analysis", "debug_helper"]],
                "updated_at": datetime.now().isoformat(),
            }
            with open(skills_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save skills: {e}")
    
    def add_skill(self, skill: Skill) -> bool:
        """添加技能"""
        self.skills[skill.id] = skill
        self._save_skills()
        logger.info(f"Added skill: {skill.name}")
        return True
    
    def remove_skill(self, skill_id: str) -> bool:
        """删除技能"""
        if skill_id in self.skills:
            del self.skills[skill_id]
            self._save_skills()
            logger.info(f"Removed skill: {skill_id}")
            return True
        return False
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """获取技能"""
        return self.skills.get(skill_id)
    
    def list_skills(self, category: Optional[str] = None) -> List[Skill]:
        """列出技能"""
        skills = list(self.skills.values())
        if category:
            skills = [s for s in skills if s.category == category]
        return [s for s in skills if s.enabled]
    
    def match_skills(self, query: str) -> List[Skill]:
        """根据查询匹配技能"""
        matched = []
        for skill in self.skills.values():
            if skill.enabled and skill.matches(query):
                matched.append(skill)
        return matched
    
    def get_enhanced_prompt(self, query: str, base_prompt: str = "") -> str:
        """
        获取技能增强的 System Prompt
        
        根据用户查询自动匹配相关技能，将技能指令添加到 Prompt 中
        """
        matched = self.match_skills(query)
        
        if not matched:
            return base_prompt
        
        # 最多使用 2 个技能避免 Prompt 过长
        matched = matched[:2]
        
        parts = [base_prompt] if base_prompt else []
        parts.append("\n\n---\n\n# 已激活技能\n")
        
        for skill in matched:
            parts.append(skill.get_prompt_extension())
            parts.append("\n---\n")
        
        logger.info(f"Activated skills: {[s.name for s in matched]}")
        return "\n".join(parts)


# ==================== 全局实例 ====================

_skills_manager: Optional[SkillsManager] = None

def get_skills_manager() -> SkillsManager:
    """获取全局 SkillsManager 实例"""
    global _skills_manager
    if _skills_manager is None:
        _skills_manager = SkillsManager()
    return _skills_manager


# ==================== 导出 ====================

__all__ = [
    "Skill",
    "SkillsManager",
    "get_skills_manager",
]


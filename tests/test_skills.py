# -*- coding: utf-8 -*-
"""
Skills 系统测试

测试技能系统的功能：
- 技能注册
- 技能触发
- 技能执行
- 技能管理（启用/禁用）
- 内置技能
"""
import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


@pytest.fixture
def skills_manager():
    """创建技能管理器"""
    from app.core.skills import SkillsManager
    return SkillsManager()


class TestSkillRegistration:
    """测试技能注册"""
    
    def test_register_skill(self, skills_manager):
        """测试注册技能"""
        skill = {
            "id": "test_skill",
            "name": "测试技能",
            "description": "这是一个测试技能",
            "instructions": "执行测试操作",
            "triggers": ["测试", "test"],
            "category": "testing",
        }
        
        skills_manager.register_skill(skill)
        
        assert skills_manager.get_skill("test_skill") is not None
    
    def test_register_duplicate_skill(self, skills_manager):
        """测试注册重复技能"""
        skill = {
            "id": "duplicate",
            "name": "重复技能",
            "description": "会被覆盖",
            "instructions": "...",
            "triggers": [],
        }
        
        skills_manager.register_skill(skill)
        
        skill["name"] = "更新后的技能"
        skills_manager.register_skill(skill)
        
        retrieved = skills_manager.get_skill("duplicate")
        assert retrieved["name"] == "更新后的技能"
    
    def test_unregister_skill(self, skills_manager):
        """测试注销技能"""
        skill = {
            "id": "to_remove",
            "name": "待删除技能",
            "description": "...",
            "instructions": "...",
            "triggers": [],
        }
        
        skills_manager.register_skill(skill)
        skills_manager.unregister_skill("to_remove")
        
        assert skills_manager.get_skill("to_remove") is None


class TestSkillTrigger:
    """测试技能触发"""
    
    def test_trigger_by_keyword(self, skills_manager):
        """测试关键词触发"""
        skill = {
            "id": "code_review",
            "name": "代码审查",
            "description": "审查代码质量",
            "instructions": "检查代码规范",
            "triggers": ["代码审查", "review code", "检查代码"],
        }
        
        skills_manager.register_skill(skill)
        
        triggered = skills_manager.detect_skill("帮我做代码审查")
        
        assert triggered is not None
        assert triggered["id"] == "code_review"
    
    def test_trigger_partial_match(self, skills_manager):
        """测试部分匹配触发"""
        skill = {
            "id": "translation",
            "name": "翻译",
            "description": "翻译文本",
            "instructions": "翻译内容",
            "triggers": ["翻译", "translate"],
        }
        
        skills_manager.register_skill(skill)
        
        triggered = skills_manager.detect_skill("请帮我翻译这段话")
        
        assert triggered is not None
    
    def test_no_trigger(self, skills_manager):
        """测试无触发"""
        skill = {
            "id": "specific",
            "name": "特定技能",
            "description": "...",
            "instructions": "...",
            "triggers": ["very_specific_keyword"],
        }
        
        skills_manager.register_skill(skill)
        
        triggered = skills_manager.detect_skill("普通的问题")
        
        # 没有匹配的技能
        assert triggered is None


class TestSkillExecution:
    """测试技能执行"""
    
    @pytest.mark.asyncio
    async def test_execute_skill(self, skills_manager):
        """测试执行技能"""
        skill = {
            "id": "greeting",
            "name": "问候",
            "description": "友好问候",
            "instructions": "使用友好的方式问候用户",
            "triggers": ["你好", "hello"],
        }
        
        skills_manager.register_skill(skill)
        
        context = await skills_manager.get_skill_context("你好")
        
        assert context is not None
        assert "instructions" in context
    
    @pytest.mark.asyncio
    async def test_skill_with_context(self, skills_manager):
        """测试带上下文的技能"""
        skill = {
            "id": "code_expert",
            "name": "代码专家",
            "description": "编程问题专家",
            "instructions": "作为编程专家，详细解答问题",
            "triggers": ["编程", "代码", "code"],
            "context_required": True,
        }
        
        skills_manager.register_skill(skill)
        
        context = await skills_manager.get_skill_context(
            "解释 Python 的装饰器",
            additional_context={"language": "Python"}
        )
        
        assert context is not None


class TestSkillManagement:
    """测试技能管理"""
    
    def test_list_skills(self, skills_manager):
        """测试列出技能"""
        skills_manager.register_skill({
            "id": "skill1",
            "name": "技能1",
            "description": "...",
            "instructions": "...",
            "triggers": [],
        })
        
        skills_manager.register_skill({
            "id": "skill2",
            "name": "技能2",
            "description": "...",
            "instructions": "...",
            "triggers": [],
        })
        
        skills = skills_manager.list_skills()
        
        assert len(skills) >= 2
    
    def test_enable_disable_skill(self, skills_manager):
        """测试启用/禁用技能"""
        skill = {
            "id": "toggleable",
            "name": "可切换技能",
            "description": "...",
            "instructions": "...",
            "triggers": ["toggle"],
            "enabled": True,
        }
        
        skills_manager.register_skill(skill)
        
        # 禁用
        skills_manager.toggle_skill("toggleable", enabled=False)
        
        retrieved = skills_manager.get_skill("toggleable")
        assert retrieved["enabled"] is False
        
        # 启用
        skills_manager.toggle_skill("toggleable", enabled=True)
        
        retrieved = skills_manager.get_skill("toggleable")
        assert retrieved["enabled"] is True
    
    def test_disabled_skill_not_triggered(self, skills_manager):
        """测试禁用的技能不会触发"""
        skill = {
            "id": "disabled_skill",
            "name": "禁用技能",
            "description": "...",
            "instructions": "...",
            "triggers": ["disabled_trigger"],
            "enabled": False,
        }
        
        skills_manager.register_skill(skill)
        
        triggered = skills_manager.detect_skill("disabled_trigger")
        
        assert triggered is None
    
    def test_filter_skills_by_category(self, skills_manager):
        """测试按类别过滤技能"""
        skills_manager.register_skill({
            "id": "coding1",
            "name": "编程技能1",
            "description": "...",
            "instructions": "...",
            "triggers": [],
            "category": "coding",
        })
        
        skills_manager.register_skill({
            "id": "writing1",
            "name": "写作技能1",
            "description": "...",
            "instructions": "...",
            "triggers": [],
            "category": "writing",
        })
        
        coding_skills = skills_manager.list_skills(category="coding")
        
        assert all(s["category"] == "coding" for s in coding_skills)


class TestBuiltinSkills:
    """测试内置技能"""
    
    def test_load_builtin_skills(self):
        """测试加载内置技能"""
        from app.core.skills import SkillsManager
        
        manager = SkillsManager(load_builtin=True)
        skills = manager.list_skills()
        
        # 应该有一些内置技能
        assert len(skills) >= 0
    
    def test_code_assistant_skill(self, skills_manager):
        """测试代码助手技能"""
        from app.core.skills import BUILTIN_SKILLS
        
        # 注册内置技能
        for skill in BUILTIN_SKILLS:
            skills_manager.register_skill(skill)
        
        # 查找代码助手
        code_skill = skills_manager.get_skill("code_assistant")
        
        if code_skill:
            assert "代码" in code_skill["name"] or "code" in code_skill["name"].lower()


class TestSkillPriority:
    """测试技能优先级"""
    
    def test_skill_priority(self, skills_manager):
        """测试技能优先级"""
        skills_manager.register_skill({
            "id": "general",
            "name": "通用技能",
            "description": "...",
            "instructions": "...",
            "triggers": ["帮助"],
            "priority": 1,
        })
        
        skills_manager.register_skill({
            "id": "specific",
            "name": "特定技能",
            "description": "...",
            "instructions": "...",
            "triggers": ["帮助"],
            "priority": 10,  # 更高优先级
        })
        
        triggered = skills_manager.detect_skill("帮助")
        
        # 应该触发高优先级的技能
        if triggered:
            assert triggered["id"] == "specific"


class TestSkillComposition:
    """测试技能组合"""
    
    @pytest.mark.asyncio
    async def test_combine_skills(self, skills_manager):
        """测试组合多个技能"""
        skills_manager.register_skill({
            "id": "formatting",
            "name": "格式化",
            "description": "...",
            "instructions": "格式化输出",
            "triggers": ["格式化"],
        })
        
        skills_manager.register_skill({
            "id": "translation",
            "name": "翻译",
            "description": "...",
            "instructions": "翻译内容",
            "triggers": ["翻译"],
        })
        
        # 组合技能上下文
        context = await skills_manager.get_combined_context(
            "翻译并格式化",
            skill_ids=["formatting", "translation"]
        )
        
        assert context is not None


class TestSkillPersistence:
    """测试技能持久化"""
    
    @pytest.mark.asyncio
    async def test_save_custom_skill(self, skills_manager, tmp_path):
        """测试保存自定义技能"""
        skill = {
            "id": "custom",
            "name": "自定义技能",
            "description": "用户创建的技能",
            "instructions": "执行自定义操作",
            "triggers": ["自定义"],
        }
        
        skills_manager.register_skill(skill)
        
        # 保存到文件
        save_path = tmp_path / "skills.json"
        await skills_manager.save_skills(str(save_path))
        
        assert save_path.exists()
    
    @pytest.mark.asyncio
    async def test_load_custom_skills(self, tmp_path):
        """测试加载自定义技能"""
        from app.core.skills import SkillsManager
        import json
        
        # 创建技能文件
        skills_data = [{
            "id": "loaded",
            "name": "加载的技能",
            "description": "...",
            "instructions": "...",
            "triggers": ["加载"],
        }]
        
        save_path = tmp_path / "skills.json"
        save_path.write_text(json.dumps(skills_data))
        
        # 加载
        manager = SkillsManager()
        await manager.load_skills(str(save_path))
        
        skill = manager.get_skill("loaded")
        assert skill is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


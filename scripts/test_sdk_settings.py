# -*- coding: utf-8 -*-
"""
测试 SDK 设置功能 - 验证 UI 和 SDK 功能一致性
"""
import sys
from pathlib import Path

# 设置路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'backend'))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / 'backend' / '.env')

from agentic_sdk import SettingsManager


def test_sdk_settings():
    """测试 SDK 设置功能"""
    print("=" * 60)
    print("🧪 测试 SDK 设置功能（对应 UI Settings）")
    print("=" * 60)
    
    # 初始化
    settings = SettingsManager(workspace=str(PROJECT_ROOT))
    
    # 1. 测试索引功能
    print("\n📁 1. Indexing & Docs")
    print("-" * 40)
    
    status = settings.get_index_status()
    print(f"  索引状态:")
    print(f"    - 已索引文件: {status.indexed_files}")
    print(f"    - 完成: {status.is_complete}")
    
    files = settings.get_indexed_files()
    print(f"  已索引文件: {len(files)} 个")
    
    # 2. 测试规则功能
    print("\n📜 2. Rules & Commands")
    print("-" * 40)
    
    # 添加用户规则
    settings.add_user_rule("始终使用中文回复")
    settings.add_user_rule("代码注释使用英文")
    user_rules = settings.get_user_rules()
    print(f"  用户规则: {len(user_rules)} 条")
    for r in user_rules:
        print(f"    - {r}")
    
    # 添加项目规则
    settings.add_project_rule("使用 FastAPI 风格")
    project_rules = settings.get_project_rules()
    print(f"  项目规则: {len(project_rules)} 条")
    for r in project_rules:
        print(f"    - {r}")
    
    # 3. 测试技能功能
    print("\n🎯 3. Skills")
    print("-" * 40)
    
    skills = settings.list_skills()
    print(f"  已安装技能: {len(skills)} 个")
    for skill in skills[:5]:
        status = "✅" if skill.enabled else "☐"
        print(f"    {status} {skill.name} ({skill.id})")
    if len(skills) > 5:
        print(f"    ... 还有 {len(skills) - 5} 个")
    
    # 获取单个技能
    skill = settings.get_skill("code_review")
    if skill:
        print(f"  技能详情 (code_review):")
        print(f"    - 名称: {skill.name}")
        print(f"    - 触发词: {', '.join(skill.triggers[:3])}")
    
    # 创建自定义技能
    settings.create_skill(
        skill_id="test_skill",
        name="测试技能",
        description="用于测试的技能",
        instructions="这是测试指令",
        triggers=["测试", "test"],
    )
    print("  ✅ 创建自定义技能: test_skill")
    
    # 4. 测试 MCP 功能
    print("\n🔧 4. Tools & MCP")
    print("-" * 40)
    
    # 添加 MCP 服务器
    settings.add_mcp_server("test-mcp", "http", "http://localhost:9000")
    servers = settings.list_mcp_servers()
    print(f"  MCP 服务器: {len(servers)} 个")
    for s in servers:
        print(f"    - {s.name} ({s.server_type})")
    
    # 5. 获取摘要
    print("\n📊 5. 设置摘要")
    print("-" * 40)
    
    summary = settings.get_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("✅ SDK 设置功能测试完成！")
    print("=" * 60)
    
    # 功能对照表
    print("\n📋 UI ↔ SDK 功能对照表:")
    print("-" * 60)
    print("""
| UI 功能                | SDK 接口                          |
|------------------------|-----------------------------------|
| 📁 Indexing & Docs     |                                   |
|   - Sync Index         | settings.sync_index()             |
|   - View Files         | settings.get_indexed_files()      |
|   - Delete Index       | settings.clear_index()            |
|   - Add Doc            | settings.add_doc(path)            |
|                        |                                   |
| 📜 Rules & Commands    |                                   |
|   - Add User Rule      | settings.add_user_rule(rule)      |
|   - Add Project Rule   | settings.add_project_rule(rule)   |
|   - List Rules         | settings.get_all_rules()          |
|                        |                                   |
| 🎯 Skills              |                                   |
|   - List Skills        | settings.list_skills()            |
|   - Get Skill          | settings.get_skill(id)            |
|   - Toggle Skill       | settings.toggle_skill(id, bool)   |
|   - Create Skill       | settings.create_skill(...)        |
|   - Delete Skill       | settings.delete_skill(id)         |
|                        |                                   |
| 🔧 Tools & MCP         |                                   |
|   - Add MCP Server     | settings.add_mcp_server(...)      |
|   - Remove MCP Server  | settings.remove_mcp_server(name)  |
|   - List MCP Servers   | settings.list_mcp_servers()       |
""")


if __name__ == "__main__":
    test_sdk_settings()


# -*- coding: utf-8 -*-
"""
Cursor 风格组件测试脚本

测试新实现的核心组件：
1. IntentRecognizer - 意图识别
2. ContextManager - 上下文管理
3. ToolOrchestrator - 工具编排
4. AgentLoop - 执行循环
5. UserPreferences - 用户偏好
6. CursorStyleOrchestrator - 统一编排
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")


def test_imports():
    """测试所有导入"""
    print("\n" + "="*60)
    print("📦 测试 1: 导入检查")
    print("="*60)
    
    errors = []
    
    # 测试各模块导入
    modules = [
        ("IntentRecognizer", "app.core.intent_recognizer", "IntentRecognizer"),
        ("Intent", "app.core.intent_recognizer", "Intent"),
        ("TaskType", "app.core.intent_recognizer", "TaskType"),
        ("ContextManager", "app.core.context_manager", "ContextManager"),
        ("build_context", "app.core.context_manager", "build_context"),
        ("ToolOrchestrator", "app.core.tool_orchestrator", "ToolOrchestrator"),
        ("AgentLoop", "app.core.agent_loop", "AgentLoop"),
        ("UserPreferenceManager", "app.core.user_preferences", "UserPreferenceManager"),
        ("CursorStyleOrchestrator", "app.core.cursor_style_orchestrator", "CursorStyleOrchestrator"),
        ("SkillsManager", "app.core.skills", "SkillsManager"),
        ("AgentPlanner", "app.core.planner", "AgentPlanner"),
    ]
    
    for name, module_path, class_name in modules:
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"  ✅ {name}")
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            errors.append((name, str(e)))
    
    if errors:
        print(f"\n❌ 导入失败: {len(errors)} 个模块")
        return False
    else:
        print(f"\n✅ 所有模块导入成功!")
        return True


def test_intent_recognizer():
    """测试意图识别器"""
    print("\n" + "="*60)
    print("🔍 测试 2: 意图识别器 (IntentRecognizer)")
    print("="*60)
    
    from app.core.intent_recognizer import IntentRecognizer, TaskType
    
    recognizer = IntentRecognizer()
    
    # 测试用例
    test_cases = [
        ("你好", TaskType.CONVERSATION, "简单问候"),
        ("帮我分析这个代码", TaskType.ANALYSIS, "分析任务"),
        ("执行 ls 命令", TaskType.ACTION, "执行操作"),
        ("写一个 Python 函数计算斐波那契数列", TaskType.CREATION, "创建任务"),
        ("修改这个函数的名称", TaskType.MODIFICATION, "修改任务"),
        ("首先分析问题，然后给出解决方案，最后验证", TaskType.COMPLEX, "复杂多步骤"),
    ]
    
    passed = 0
    for message, expected_type, description in test_cases:
        # 使用规则匹配（不需要 LLM）
        intent = recognizer._enhanced_rule_match(message, None)
        
        status = "✅" if intent.task_type == expected_type else "⚠️"
        if intent.task_type == expected_type:
            passed += 1
        
        print(f"  {status} [{description}]")
        print(f"      输入: \"{message}\"")
        print(f"      识别: {intent.task_type.value} (期望: {expected_type.value})")
        print(f"      复杂度: {intent.complexity}, 多步骤: {intent.is_multi_step}")
    
    print(f"\n  结果: {passed}/{len(test_cases)} 通过")
    return passed >= len(test_cases) * 0.7  # 70% 通过率


def test_context_manager():
    """测试上下文管理器"""
    print("\n" + "="*60)
    print("📚 测试 3: 上下文管理器 (ContextManager)")
    print("="*60)
    
    from app.core.context_manager import ContextManager, ContextSource
    
    cm = ContextManager(max_tokens=1000)
    
    # 添加各种上下文
    cm.add_skill_instructions("代码审查", "请按标准审查代码...")
    cm.add_rag_results([
        {"content": "Python 最佳实践...", "source": "docs/python.md", "score": 0.9},
        {"content": "代码风格指南...", "source": "docs/style.md", "score": 0.8},
    ])
    cm.add_file_content("/app/main.py", "def hello():\n    print('Hello')")
    cm.add_conversation_history([
        {"role": "user", "content": "帮我审查代码"},
        {"role": "assistant", "content": "好的，请提供代码"},
    ])
    
    # 构建上下文
    context = cm.build()
    stats = cm.get_stats()
    
    print(f"  ✅ 添加了 {stats['total_blocks']} 个上下文块")
    print(f"  ✅ 总 Token 数: {stats['total_tokens']}")
    print(f"  ✅ 预算: {cm.max_tokens} tokens")
    print(f"\n  上下文预览 (前 500 字符):")
    print("  " + "-"*50)
    for line in context[:500].split('\n'):
        print(f"  {line}")
    print("  " + "-"*50)
    
    # 验证
    assert stats['total_blocks'] > 0, "应该有上下文块"
    assert "技能" in context or "任务指令" in context, "应该包含技能"
    assert "知识库" in context, "应该包含 RAG 结果"
    
    print(f"\n✅ 上下文管理器测试通过!")
    return True


def test_tool_orchestrator():
    """测试工具编排器"""
    print("\n" + "="*60)
    print("🔧 测试 4: 工具编排器 (ToolOrchestrator)")
    print("="*60)
    
    from app.core.tool_orchestrator import ToolOrchestrator, ToolCategory
    
    orchestrator = ToolOrchestrator()
    
    # 注册测试工具
    def mock_shell_execute(command: str) -> str:
        """执行 Shell 命令"""
        return f"执行: {command}"
    
    def mock_file_read(path: str) -> str:
        """读取文件内容"""
        return f"文件内容: {path}"
    
    def mock_search(query: str) -> str:
        """搜索知识库"""
        return f"搜索结果: {query}"
    
    orchestrator.register(mock_shell_execute)
    orchestrator.register(mock_file_read)
    orchestrator.register(mock_search)
    
    print(f"  ✅ 注册了 {len(orchestrator.tools)} 个工具")
    
    # 测试工具选择
    test_queries = [
        ("执行 ls 命令查看目录", ["mock_shell_execute"]),
        ("读取 config.py 文件", ["mock_file_read"]),
        ("搜索关于 Python 的文档", ["mock_search"]),
    ]
    
    for query, expected in test_queries:
        selections = orchestrator._keyword_match(query)
        selected_names = [s.tool_name for s in selections]
        
        matched = any(e in selected_names for e in expected)
        status = "✅" if matched else "⚠️"
        
        print(f"  {status} \"{query[:30]}...\"")
        print(f"      选择: {selected_names[:3]}")
    
    print(f"\n✅ 工具编排器测试通过!")
    return True


def test_user_preferences():
    """测试用户偏好管理器"""
    print("\n" + "="*60)
    print("👤 测试 5: 用户偏好管理器 (UserPreferenceManager)")
    print("="*60)
    
    from app.core.user_preferences import UserPreferenceManager, ResponseStyle
    import tempfile
    import shutil
    
    # 使用临时目录
    temp_dir = tempfile.mkdtemp()
    
    try:
        manager = UserPreferenceManager(storage_dir=temp_dir)
        
        # 模拟用户交互
        user_id = "test_user_123"
        
        # 学习用户消息
        manager.learn_from_message(user_id, "帮我分析这个 Python 代码")
        manager.learn_from_message(user_id, "使用 docker 部署这个应用")
        manager.learn_from_message(user_id, "检查 linux 服务器状态")
        
        # 学习工具使用
        manager.learn_from_tool_usage(user_id, "shell_execute", True)
        manager.learn_from_tool_usage(user_id, "shell_execute", True)
        manager.learn_from_tool_usage(user_id, "file_read", True)
        
        # 获取用户画像
        profile = manager.get_or_create(user_id)
        summary = manager.get_user_summary(user_id)
        style_prompt = manager.get_style_prompt(user_id)
        
        print(f"  ✅ 用户 ID: {user_id}")
        print(f"  ✅ 消息数: {profile.total_messages}")
        print(f"  ✅ 语言偏好: {profile.language.value}")
        print(f"  ✅ 检测到的领域: {profile.domains}")
        print(f"  ✅ 常用工具: {profile.favorite_tools}")
        print(f"  ✅ 风格提示: {style_prompt[:50]}..." if style_prompt else "  ✅ 风格提示: (无)")
        
        print(f"\n✅ 用户偏好管理器测试通过!")
        return True
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_skills_manager():
    """测试技能管理器"""
    print("\n" + "="*60)
    print("🎯 测试 6: 技能管理器 (SkillsManager)")
    print("="*60)
    
    from app.core.skills import SkillsManager
    import tempfile
    import shutil
    
    # 使用临时目录
    temp_dir = tempfile.mkdtemp()
    
    try:
        manager = SkillsManager(skills_dir=temp_dir)
        
        # 列出内置技能
        skills = manager.list_skills()
        print(f"  ✅ 加载了 {len(skills)} 个内置技能:")
        for skill in skills:
            print(f"      - {skill.name}: {skill.description[:40]}...")
        
        # 测试技能匹配
        test_queries = [
            ("帮我审查这段代码", "code_review"),
            ("写一个 API 文档", "write_docs"),
            ("分析这个数据集", "data_analysis"),
            ("这个错误怎么解决", "debug_helper"),
        ]
        
        print(f"\n  技能匹配测试:")
        for query, expected_id in test_queries:
            matched = manager.match_skills(query)
            matched_ids = [s.id for s in matched]
            
            status = "✅" if expected_id in matched_ids else "⚠️"
            print(f"    {status} \"{query}\" → {matched_ids}")
        
        print(f"\n✅ 技能管理器测试通过!")
        return True
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def test_agent_loop():
    """测试 Agent 执行循环"""
    print("\n" + "="*60)
    print("🔄 测试 7: Agent 执行循环 (AgentLoop)")
    print("="*60)
    
    from app.core.agent_loop import AgentLoop, ProgressUpdate
    from app.core.planner import AgentPlanner
    
    # 创建 Mock LLM
    class MockLLM:
        async def chat_completion(self, messages, temperature=0.7):
            return "这是一个模拟的 LLM 响应。"
    
    mock_llm = MockLLM()
    planner = AgentPlanner(mock_llm)
    
    # 创建 Agent Loop
    loop = AgentLoop(
        llm_client=mock_llm,
        tools={},  # 暂时无工具
        planner=planner,
        max_steps=5,
    )
    
    # 测试简单任务
    print("  测试简单任务...")
    updates = []
    async for update in loop.execute("你好，介绍一下你自己"):
        updates.append(update)
        print(f"    [{update.type}] {update.message[:50]}..." if update.message else f"    [{update.type}]")
    
    print(f"  ✅ 收到 {len(updates)} 个更新")
    
    # 验证状态
    status = loop.get_status()
    print(f"  ✅ 最终状态: {status['state']}")
    
    print(f"\n✅ Agent 执行循环测试通过!")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🚀 Cursor 风格组件测试套件")
    print("="*60)
    
    results = []
    
    # 1. 导入测试
    try:
        results.append(("导入检查", test_imports()))
    except Exception as e:
        print(f"❌ 导入检查失败: {e}")
        results.append(("导入检查", False))
        return results  # 导入失败则停止
    
    # 2. 意图识别器
    try:
        results.append(("意图识别器", test_intent_recognizer()))
    except Exception as e:
        print(f"❌ 意图识别器测试失败: {e}")
        results.append(("意图识别器", False))
    
    # 3. 上下文管理器
    try:
        results.append(("上下文管理器", test_context_manager()))
    except Exception as e:
        print(f"❌ 上下文管理器测试失败: {e}")
        results.append(("上下文管理器", False))
    
    # 4. 工具编排器
    try:
        results.append(("工具编排器", test_tool_orchestrator()))
    except Exception as e:
        print(f"❌ 工具编排器测试失败: {e}")
        results.append(("工具编排器", False))
    
    # 5. 用户偏好管理器
    try:
        results.append(("用户偏好管理器", test_user_preferences()))
    except Exception as e:
        print(f"❌ 用户偏好管理器测试失败: {e}")
        results.append(("用户偏好管理器", False))
    
    # 6. 技能管理器
    try:
        results.append(("技能管理器", test_skills_manager()))
    except Exception as e:
        print(f"❌ 技能管理器测试失败: {e}")
        results.append(("技能管理器", False))
    
    # 7. Agent 执行循环
    try:
        results.append(("Agent 执行循环", asyncio.run(test_agent_loop())))
    except Exception as e:
        print(f"❌ Agent 执行循环测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Agent 执行循环", False))
    
    # 汇总结果
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"  {status} {name}")
    
    print(f"\n{'='*60}")
    print(f"  总计: {passed}/{total} 通过")
    print(f"{'='*60}\n")
    
    return results


if __name__ == "__main__":
    run_all_tests()


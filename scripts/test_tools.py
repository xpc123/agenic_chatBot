#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试工具注册和沙箱执行

运行: python scripts/test_tools.py
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger


def test_sandbox():
    """测试沙箱执行"""
    print("\n" + "="*60)
    print("🧪 测试沙箱执行")
    print("="*60)
    
    from backend.app.core.sandbox import Sandbox, safe_exec
    
    sandbox = Sandbox()
    
    # 测试 1: 基本执行
    print("\n📝 测试 1: 基本代码执行")
    result = sandbox.execute_python("print('Hello, Sandbox!')")
    print(f"状态: {result.status.value}")
    print(f"输出: {result.output}")
    print(f"耗时: {result.execution_time_ms:.2f}ms")
    
    # 测试 2: 数学计算
    print("\n📝 测试 2: 数学计算")
    result = sandbox.execute_python("""
import math
print(f"π = {math.pi}")
print(f"sin(30°) = {math.sin(math.radians(30))}")
print(f"斐波那契: {[1,1,2,3,5,8,13,21]}")
""")
    print(f"状态: {result.status.value}")
    print(f"输出: {result.output}")
    
    # 测试 3: 安全拦截
    print("\n📝 测试 3: 危险操作拦截")
    result = sandbox.execute_python("import os; os.system('ls')")
    print(f"状态: {result.status.value}")
    print(f"错误: {result.error[:200] if result.error else 'None'}")
    
    # 测试 4: 超时控制
    print("\n📝 测试 4: 超时控制 (设置 2 秒)")
    from backend.app.core.sandbox import SandboxConfig
    short_sandbox = Sandbox(SandboxConfig(timeout_seconds=2))
    result = short_sandbox.execute_python("""
import time
time.sleep(10)
print("不应该输出")
""")
    print(f"状态: {result.status.value}")
    print(f"错误: {result.error}")
    
    # 测试 5: 简化接口
    print("\n📝 测试 5: safe_exec 简化接口")
    output = safe_exec("print([i**2 for i in range(10)])")
    print(output)
    
    print("\n✅ 沙箱测试完成")


def test_tool_registry():
    """测试工具注册表"""
    print("\n" + "="*60)
    print("🧪 测试工具注册表")
    print("="*60)
    
    from backend.app.core.tool_registry import (
        ToolRegistry, ToolPermission, APIToolConfig
    )
    from backend.app.core.tools import calculator, get_current_time
    
    registry = ToolRegistry()
    
    # 测试 1: 注册工具
    print("\n📝 测试 1: 注册内置工具")
    registry.register(calculator, permission=ToolPermission.PUBLIC)
    registry.register(get_current_time, permission=ToolPermission.PUBLIC)
    print(f"已注册工具: {registry.get_tool_names()}")
    
    # 测试 2: 获取工具
    print("\n📝 测试 2: 获取工具")
    tools = registry.get_all_tools()
    print(f"可用工具数量: {len(tools)}")
    for t in tools:
        print(f"  - {t.name}: {t.description[:50]}...")
    
    # 测试 3: 禁用工具
    print("\n📝 测试 3: 禁用/启用工具")
    registry.disable("calculator")
    print(f"禁用后可用工具: {len(registry.get_all_tools())}")
    registry.enable("calculator")
    print(f"启用后可用工具: {len(registry.get_all_tools())}")
    
    # 测试 4: 工具信息
    print("\n📝 测试 4: 工具元数据")
    meta = registry.get_metadata("calculator")
    if meta:
        print(f"名称: {meta.name}")
        print(f"权限: {meta.permission.value}")
        print(f"分类: {meta.category}")
    
    # 测试 5: 按权限过滤
    print("\n📝 测试 5: 按权限过滤")
    public_tools = registry.get_tools(permissions={ToolPermission.PUBLIC})
    print(f"公开工具数量: {len(public_tools)}")
    
    # 测试 6: 统计
    print("\n📝 测试 6: 统计信息")
    registry.record_call("calculator", success=True, latency_ms=10.5)
    registry.record_call("calculator", success=True, latency_ms=8.3)
    stats = registry.get_stats()
    print(f"统计: {stats}")
    
    print("\n✅ 工具注册表测试完成")


def test_api_tool():
    """测试 API 工具创建（不实际调用）"""
    print("\n" + "="*60)
    print("🧪 测试 API 工具配置")
    print("="*60)
    
    from backend.app.core.tool_registry import ToolRegistry, APIToolConfig, ToolPermission
    
    registry = ToolRegistry()
    
    # 创建 API 工具配置
    config = APIToolConfig(
        name="test_api",
        description="测试 API 工具",
        url="https://httpbin.org/get",
        method="GET",
        parameters=[
            {"name": "query", "type": "string", "description": "查询参数", "required": False}
        ],
        permission=ToolPermission.BASIC,
    )
    
    print(f"API 配置: {config.name}")
    print(f"  URL: {config.url}")
    print(f"  方法: {config.method}")
    print(f"  参数: {config.parameters}")
    
    # 注册（仅验证配置）
    success = registry.register_api_tool(config)
    print(f"注册结果: {'✅ 成功' if success else '❌ 失败'}")
    
    if success:
        tools = registry.list_tools()
        print(f"工具列表: {tools}")
    
    print("\n✅ API 工具配置测试完成")


def test_new_tools():
    """测试新添加的工具"""
    print("\n" + "="*60)
    print("🧪 测试新工具")
    print("="*60)
    
    from backend.app.core.tools import (
        http_request, get_system_info, run_python_code
    )
    
    # 测试系统信息
    print("\n📝 测试系统信息工具")
    result = get_system_info.invoke({})
    print(result)
    
    # 测试 Python 执行（使用新沙箱）
    print("\n📝 测试 Python 执行（新沙箱）")
    result = run_python_code.invoke({"code": "print(sum(range(100)))"})
    print(result)
    
    # 测试危险代码拦截
    print("\n📝 测试危险代码拦截")
    result = run_python_code.invoke({"code": "import os\nos.listdir('/')"})
    print(result)
    
    print("\n✅ 新工具测试完成")


def main():
    """运行所有测试"""
    print("🚀 开始工具系统测试")
    print("="*60)
    
    try:
        test_sandbox()
        test_tool_registry()
        test_api_tool()
        test_new_tools()
        
        print("\n" + "="*60)
        print("🎉 所有测试通过！")
        print("="*60)
        
    except Exception as e:
        logger.exception("测试失败")
        print(f"\n❌ 测试失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/bin/bash
# Agentic ChatBot SDK 测试脚本
#
# 用法:
#   ./tests/run_tests.sh           # 运行所有测试
#   ./tests/run_tests.sh quick     # 快速测试
#   ./tests/run_tests.sh file      # 只测试文件操作
#   ./tests/run_tests.sh memory    # 只测试记忆功能

cd /ADE1/users/xpengche/project/agentic_chatBot
source backend/venv/bin/activate

echo "🧪 Agentic ChatBot SDK 测试"
echo "=========================="

case "$1" in
    quick)
        echo "⚡ 快速测试模式"
        python tests/test_sdk_comprehensive.py --quick 2>&1 | grep -E "^\[|✅|❌|📊|通过|失败|总计"
        ;;
    file)
        echo "📁 文件操作测试"
        python tests/test_sdk_comprehensive.py -c file_operation 2>&1 | grep -E "^\[|✅|❌|📊|通过|失败|总计"
        ;;
    memory)
        echo "🧠 记忆功能测试"
        python tests/test_sdk_comprehensive.py -c memory 2>&1 | grep -E "^\[|✅|❌|📊|通过|失败|总计"
        ;;
    conversation)
        echo "💬 对话测试"
        python tests/test_sdk_comprehensive.py -c conversation qa 2>&1 | grep -E "^\[|✅|❌|📊|通过|失败|总计"
        ;;
    cursor)
        echo "🎯 Cursor/Copilot 对标测试"
        python tests/test_sdk_comprehensive.py -c cursor_like 2>&1 | grep -E "^\[|✅|❌|📊|通过|失败|总计"
        ;;
    pytest)
        echo "🔬 Pytest 模式"
        python -m pytest tests/test_sdk_comprehensive.py -v
        ;;
    all)
        echo "📋 完整测试"
        python tests/test_sdk_comprehensive.py 2>&1 | grep -E "^\[|✅|❌|📊|通过|失败|总计|按类别"
        ;;
    *)
        echo "用法: $0 {quick|file|memory|conversation|cursor|pytest|all}"
        echo ""
        echo "可用测试类别:"
        echo "  quick        - 快速测试 (TRIVIAL + LOW 复杂度)"
        echo "  file         - 文件操作测试"
        echo "  memory       - 记忆功能测试"
        echo "  conversation - 对话测试"
        echo "  cursor       - Cursor/Copilot 对标测试"
        echo "  pytest       - 使用 pytest 框架"
        echo "  all          - 完整测试"
        ;;
esac


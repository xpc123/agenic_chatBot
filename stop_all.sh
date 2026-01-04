#!/bin/bash
# Agentic ChatBot - 停止脚本

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🛑 停止 Agentic ChatBot..."

# 读取 PID 文件
if [ -f "$PROJECT_DIR/.backend.pid" ]; then
    BACKEND_PID=$(cat "$PROJECT_DIR/.backend.pid")
    if kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID
        echo "✅ 后端已停止 (PID: $BACKEND_PID)"
    fi
    rm -f "$PROJECT_DIR/.backend.pid"
fi

if [ -f "$PROJECT_DIR/.frontend.pid" ]; then
    FRONTEND_PID=$(cat "$PROJECT_DIR/.frontend.pid")
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        kill $FRONTEND_PID
        echo "✅ 前端已停止 (PID: $FRONTEND_PID)"
    fi
    rm -f "$PROJECT_DIR/.frontend.pid"
fi

# 也尝试杀掉相关进程
pkill -f "python run.py" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

echo "🎉 服务已停止"


#!/bin/bash
# Agentic ChatBot - 一键启动脚本
# 同时启动后端和前端

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "🚀 Agentic ChatBot - 启动中..."
echo "📁 项目目录: $PROJECT_DIR"

# 检查 .env 文件
if [ ! -f "$PROJECT_DIR/backend/.env" ]; then
    echo ""
    echo "⚠️  未找到 backend/.env 配置文件"
    echo "   请先运行: bash quick_install.sh"
    echo "   并配置 OPENAI_API_KEY"
    exit 1
fi

# 检查 API Key
if grep -q "your_openai_key_here" "$PROJECT_DIR/backend/.env" 2>/dev/null; then
    echo ""
    echo "⚠️  请在 backend/.env 中配置真实的 OPENAI_API_KEY"
    exit 1
fi

# 启动后端
echo ""
echo "🔧 启动后端服务..."
cd "$PROJECT_DIR/backend"

if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ 未找到虚拟环境，请先运行: bash quick_install.sh"
    exit 1
fi

# 后台启动后端
python run.py &
BACKEND_PID=$!
echo "✅ 后端已启动 (PID: $BACKEND_PID)"

# 等待后端就绪
echo "⏳ 等待后端就绪..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ 后端已就绪"
        break
    fi
    sleep 1
done

# 启动前端
echo ""
echo "🎨 启动前端服务..."
cd "$PROJECT_DIR/frontend"

if [ ! -d "node_modules" ]; then
    echo "📦 安装前端依赖..."
    npm install
fi

# 后台启动前端
npm run dev &
FRONTEND_PID=$!
echo "✅ 前端已启动 (PID: $FRONTEND_PID)"

# 完成
echo ""
echo "============================================"
echo "🎉 Agentic ChatBot 启动成功！"
echo "============================================"
echo ""
echo "🌐 访问地址:"
echo "   Web UI:    http://localhost:5173"
echo "   API Docs:  http://localhost:8000/docs"
echo ""
echo "📝 进程信息:"
echo "   后端 PID: $BACKEND_PID"
echo "   前端 PID: $FRONTEND_PID"
echo ""
echo "🛑 停止服务: kill $BACKEND_PID $FRONTEND_PID"
echo ""

# 保存 PID 到文件
echo "$BACKEND_PID" > "$PROJECT_DIR/.backend.pid"
echo "$FRONTEND_PID" > "$PROJECT_DIR/.frontend.pid"

# 等待
wait


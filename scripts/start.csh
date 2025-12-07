#!/bin/csh
# Agentic ChatBot 快速启动脚本 (csh/tcsh)
# 用于快速启动开发环境

# 获取脚本所在目录
set SCRIPT_DIR = `dirname $0`
set PROJECT_ROOT = `cd $SCRIPT_DIR/.. && pwd`

echo "🚀 启动 Agentic ChatBot..."
echo "📁 项目目录: $PROJECT_ROOT"
echo ""

# 切换到项目根目录
cd $PROJECT_ROOT

# 检查Python版本
set PYTHON_VERSION=`python3 --version 2>&1 | awk '{print $2}'`
echo "✓ Python版本: $PYTHON_VERSION"

# 检查虚拟环境
if (! -d backend/venv) then
    echo "⚠️  虚拟环境不存在，正在创建..."
    cd backend
    python3 -m venv venv
    cd ..
    echo "✓ 虚拟环境已创建"
endif

# 激活虚拟环境
echo "✓ 激活虚拟环境..."
source backend/venv/bin/activate.csh

# 检查依赖
echo "✓ 检查依赖..."
if (! -f backend/.env) then
    echo "⚠️  配置文件不存在，正在创建..."
    cp backend/.env.example backend/.env
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️  重要：请编辑 backend/.env 文件并配置："
    echo "   - OPENAI_API_KEY=your_key_here"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    read -p "配置完成后按回车继续..."
endif

# 安装Python依赖
echo "✓ 安装Python依赖..."
pip install -q -r backend/requirements.txt

# 创建必要目录
echo "✓ 创建数据目录..."
mkdir -p backend/data/documents
mkdir -p backend/data/memory
mkdir -p backend/data/vector_db/chroma
mkdir -p backend/data/vector_db/faiss
mkdir -p backend/logs

# 启动后端
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 启动后端服务..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd backend
python run.py &
set BACKEND_PID=$!

# 等待后端启动
echo "⏳ 等待后端启动..."
sleep 3

# 检查后端状态
curl -s http://localhost:8000/health > /dev/null
if ($? == 0) then
    echo "✅ 后端启动成功！"
    echo "   API地址: http://localhost:8000"
    echo "   API文档: http://localhost:8000/docs"
else
    echo "❌ 后端启动失败，请检查日志"
    kill $BACKEND_PID
    exit 1
endif

cd ..

# 检查是否需要启动前端
echo ""
read -p "是否启动前端？(y/n) " START_FRONTEND

if ("$START_FRONTEND" == "y" || "$START_FRONTEND" == "Y") then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🎨 启动前端服务..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    cd frontend
    
    # 检查node_modules
    if (! -d node_modules) then
        echo "⚠️  依赖不存在，正在安装..."
        npm install
    endif
    
    # 启动前端开发服务器
    npm run dev &
    set FRONTEND_PID=$!
    
    cd ..
    
    echo ""
    echo "✅ 前端启动成功！"
    echo "   界面地址: http://localhost:5173"
endif

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Agentic ChatBot 启动完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 访问地址："
echo "   • 前端界面: http://localhost:5173"
echo "   • API文档:  http://localhost:8000/docs"
echo "   • 健康检查: http://localhost:8000/health"
echo ""
echo "🛑 停止服务："
echo "   • 前端: Ctrl+C"
echo "   • 后端: kill $BACKEND_PID"
echo ""
echo "📚 更多文档："
echo "   • 快速开始: docs/QUICKSTART.md"
echo "   • 架构说明: docs/ARCHITECTURE.md"
echo "   • 项目目标: TARGET.md"
echo ""

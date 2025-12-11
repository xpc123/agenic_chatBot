#!/bin/bash
# Agentic ChatBot - 一键安装脚本 (Bash)
# 5 分钟快速部署

set -e

echo "🚀 Agentic ChatBot - 一键安装"
echo "================================"

# 检查 Python 版本
echo ""
echo "📋 检查系统环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python 3，请先安装 Python 3.11+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✓ Python 版本: $PYTHON_VERSION"

# 创建虚拟环境
echo ""
echo "📦 创建虚拟环境..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ 虚拟环境已创建"
else
    echo "✓ 虚拟环境已存在"
fi

# 激活虚拟环境
source venv/bin/activate

# 升级 pip
echo ""
echo "📦 升级 pip..."
pip install --upgrade pip -q

# 安装依赖
echo ""
echo "📦 安装依赖包 (这可能需要几分钟)..."
pip install -r requirements.txt -q
echo "✓ 依赖包安装完成"

# 配置环境变量
echo ""
echo "⚙️  配置环境变量..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✓ 已创建 .env 文件"
        echo ""
        echo "⚠️  请编辑 backend/.env 文件，填入你的 API 密钥:"
        echo "   - OPENAI_API_KEY=your_openai_key"
    else
        cat > .env << 'EOF'
# LLM Provider Configuration
OPENAI_API_KEY=your_openai_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# Application Configuration
APP_NAME=Agentic ChatBot
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# MCP Configuration
MCP_SERVERS_CONFIG=config/mcp_servers.json

# RAG Configuration
VECTOR_DB_TYPE=chromadb
VECTOR_DB_PATH=data/vector_db
EOF
        echo "✓ 已创建默认 .env 文件"
        echo ""
        echo "⚠️  请编辑 backend/.env 文件，填入你的 API 密钥"
    fi
else
    echo "✓ .env 文件已存在"
fi

# 创建必要的目录
echo ""
echo "📁 创建数据目录..."
mkdir -p data/vector_db/chroma
mkdir -p data/vector_db/faiss
mkdir -p data/documents
mkdir -p data/memory
mkdir -p logs
echo "✓ 数据目录已创建"

# 完成
echo ""
echo "✅ 安装完成！"
echo ""
echo "📝 下一步："
echo "   1. 编辑 backend/.env，填入你的 OPENAI_API_KEY"
echo "   2. 运行: cd backend && source venv/bin/activate"
echo "   3. 启动: python run.py"
echo "   4. 访问: http://localhost:8000/docs"
echo ""
echo "📖 快速集成文档: docs/QUICKSTART.md"
echo ""

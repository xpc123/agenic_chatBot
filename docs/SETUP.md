# Backend Setup Guide

> 📍 本文档已移至 `docs/` 目录，路径相对于项目根目录

## 快速开始

### 1. 创建并激活虚拟环境

```bash
# 从项目根目录开始
cd backend
python3 -m venv venv

# 激活虚拟环境 (csh/tcsh)
source venv/bin/activate.csh

# 或者使用便捷脚本
source activate.csh

# 或者使用项目根目录的启动脚本
cd ..
source scripts/start.csh
```

### 2. 安装依赖

```bash
# 升级 pip
pip install --upgrade pip

# 安装所有依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的 API 密钥
vi .env
```

必须配置的变量：
- `OPENAI_API_KEY`: OpenAI API 密钥

### 4. 创建必要的目录

```bash
mkdir -p data/vector_db/chroma
mkdir -p data/vector_db/faiss
mkdir -p data/documents
mkdir -p logs
```

### 5. 运行开发服务器

```bash
# 启动 FastAPI 服务器
python run.py

# 或使用 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问：
- API 文档: http://localhost:8000/docs
- WebSocket 测试: http://localhost:8000/api/v1/chat/ws/test

## 开发工作流

### 激活环境
```bash
cd backend
source activate.csh
```

### 运行测试
```bash
pytest tests/unit/ -v
pytest tests/unit/ --cov=app --cov-report=html
```

### 代码格式化
```bash
black app/
```

### 检查依赖
```bash
pip list
pip freeze > requirements.txt
```

## 项目结构

```
backend/
├── venv/                    # 虚拟环境（不提交到 git）
├── app/                     # 应用代码
│   ├── api/                # API 路由
│   ├── core/               # 核心逻辑（Agent, Planner, Executor）
│   ├── llm/                # LLM 客户端
│   ├── mcp/                # MCP 协议实现
│   ├── models/             # 数据模型
│   ├── rag/                # RAG 检索系统
│   └── config.py           # 配置管理
├── config/                  # 配置文件
│   └── mcp_servers.json    # MCP 服务器配置
├── data/                    # 数据目录（不提交到 git）
├── logs/                    # 日志目录（不提交到 git）
├── tests/                   # 测试代码
├── requirements.txt         # Python 依赖
├── run.py                   # 启动脚本
└── .env                     # 环境变量（不提交到 git）
```

## 故障排查

### 虚拟环境问题
```bash
# 删除旧的虚拟环境
rm -rf venv

# 重新创建
python3 -m venv venv
source venv/bin/activate.csh
pip install -r requirements.txt
```

### 依赖冲突
```bash
# 查看依赖树
pip install pipdeptree
pipdeptree

# 强制重装某个包
pip install --force-reinstall package_name
```

### 端口被占用
```bash
# 查找占用端口的进程
lsof -i :8000

# 杀死进程
kill -9 <PID>

# 或使用其他端口
uvicorn app.main:app --port 8001
```

## 生产部署

参考根目录的 `docker-compose.yml` 使用 Docker 部署。

```bash
cd ..
docker-compose up -d
```

## 相关文档

- [项目架构](./ARCHITECTURE.md)
- [LangChain 1.0 指南](./LANGCHAIN_1.0.md)
- [功能状态](./FEATURE_STATUS.md)
- [文档索引](./README.md)

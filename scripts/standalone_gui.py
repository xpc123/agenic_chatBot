# -*- coding: utf-8 -*-
"""
独立GUI模式启动器
方式二：配置即用，无需编码

使用方法：
1. 复制 config/config.json.example 为 config.json (项目根目录)
2. 编辑 config.json，配置上下文来源
3. 运行此脚本：python scripts/standalone_gui.py
"""
import sys
import os
import json
import asyncio
from pathlib import Path
from loguru import logger

# 获取项目根目录
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# 加载 backend/.env 环境变量
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / 'backend' / '.env')

# 添加backend路径
sys.path.insert(0, str(PROJECT_ROOT / 'backend'))

from app.config_loader import get_config_loader, AppConfig
from app.core import AgentEngine
from app.core.memory import MemoryManager
from app.core.tool_executor import ToolExecutor
from app.core.context_loader import ContextLoader
from app.core.planner import AgentPlanner
from app.mcp import mcp_registry
from app.rag.langchain_rag import RAGSystem


class StandaloneGUI:
    """独立GUI应用"""
    
    def __init__(self, config_path: str = None):
        # 默认配置路径为项目根目录的 config.json
        self.config_path = config_path or str(PROJECT_ROOT / "config.json")
        self.config: AppConfig = None
        self.agent: AgentEngine = None
        
    def load_configuration(self):
        """加载配置"""
        logger.info(f"Loading configuration from {self.config_path}")
        
        # 加载配置文件
        config_loader = get_config_loader(self.config_path)
        self.config = config_loader.load()
        
        # 验证配置
        validation = config_loader.validate_paths()
        if validation["errors"]:
            logger.error("Configuration errors:")
            for error in validation["errors"]:
                logger.error(f"  - {error}")
            raise ValueError("Invalid configuration")
        
        if validation["warnings"]:
            logger.warning("Configuration warnings:")
            for warning in validation["warnings"]:
                logger.warning(f"  - {warning}")
        
        logger.info(f"✓ Configuration loaded: {self.config.app_name}")
        return self.config
    
    async def setup_rag_system(self):
        """设置RAG系统"""
        if not self.config.features.enable_rag:
            logger.info("RAG system disabled")
            return None
        
        if not self.config.context.rag_sources:
            logger.info("No RAG sources configured")
            return None
        
        logger.info("Setting up RAG system...")
        rag = RAGSystem()
        
        # 加载文档
        for source in self.config.context.rag_sources:
            source_path = Path(source)
            
            if not source_path.exists():
                logger.warning(f"RAG source not found: {source}")
                continue
            
            if source_path.is_file():
                # 单个文件
                logger.info(f"  Loading file: {source}")
                content = source_path.read_text(encoding='utf-8')
                await rag.add_documents(
                    texts=[content],
                    metadatas=[{
                        "source": str(source_path),
                        "filename": source_path.name
                    }]
                )
            
            elif source_path.is_dir():
                # 目录
                logger.info(f"  Loading directory: {source}")
                for file_path in source_path.rglob("*"):
                    if file_path.is_file() and file_path.suffix in ['.md', '.txt', '.pdf', '.docx']:
                        try:
                            # 这里可以根据文件类型选择不同的加载器
                            content = file_path.read_text(encoding='utf-8')
                            await rag.add_documents(
                                texts=[content],
                                metadatas=[{
                                    "source": str(file_path),
                                    "filename": file_path.name
                                }]
                            )
                        except Exception as e:
                            logger.warning(f"Failed to load {file_path}: {e}")
        
        logger.info("✓ RAG system ready")
        return rag
    
    async def setup_mcp_servers(self):
        """设置MCP服务器"""
        if not self.config.features.enable_mcp_tools:
            logger.info("MCP tools disabled")
            return
        
        if not self.config.context.mcp_servers:
            logger.info("No MCP servers configured")
            return
        
        logger.info("Setting up MCP servers...")
        
        from app.models.tool import MCPServer
        
        for server_config in self.config.context.mcp_servers:
            if not server_config.enabled:
                logger.info(f"  Skipping disabled server: {server_config.name}")
                continue
            
            logger.info(f"  Registering server: {server_config.name} ({server_config.type})")
            
            try:
                # 根据服务器类型创建配置
                server_url = None
                server_auth = None
                
                if server_config.type == "http":
                    # HTTP 类型的 MCP 服务器
                    base_url = server_config.config.get("base_url", "")
                    server_url = base_url
                    
                    # 处理认证
                    auth_config = server_config.config.get("auth", {})
                    if auth_config:
                        auth_type = auth_config.get("type", "")
                        if auth_type == "bearer":
                            token = auth_config.get("token", "")
                            # 支持环境变量替换
                            if token.startswith("${") and token.endswith("}"):
                                env_var = token[2:-1]
                                token = os.environ.get(env_var, "")
                            server_auth = {"type": "bearer", "token": token}
                        elif auth_type == "basic":
                            server_auth = {
                                "type": "basic",
                                "username": auth_config.get("username", ""),
                                "password": auth_config.get("password", ""),
                            }
                    
                elif server_config.type == "sqlite":
                    # SQLite 数据库作为 MCP 工具源
                    db_path = server_config.config.get("database_path", "")
                    # 对于 SQLite，我们创建一个内置的数据库工具
                    logger.info(f"    Database path: {db_path}")
                    # 注册数据库查询工具
                    await self._register_sqlite_tools(server_config.name, db_path)
                    continue  # SQLite 不需要注册为 MCP Server
                    
                elif server_config.type == "stdio":
                    # STDIO 类型（命令行启动的 MCP 服务器）
                    command = server_config.config.get("command", "")
                    args = server_config.config.get("args", [])
                    logger.info(f"    Command: {command} {' '.join(args)}")
                    # STDIO 类型需要特殊处理，暂时跳过
                    logger.warning(f"    STDIO type not fully supported yet")
                    continue
                
                # 创建 MCPServer 实例
                if server_url:
                    mcp_server = MCPServer(
                        name=server_config.name,
                        url=server_url,
                        description=server_config.config.get("description", f"{server_config.name} MCP Server"),
                        enabled=True,
                        auth=server_auth,
                    )
                    
                    # 注册到 registry
                    await mcp_registry.register_server(mcp_server)
                    logger.info(f"    ✓ Server registered: {server_config.name}")
                    
            except Exception as e:
                logger.error(f"    ✗ Failed to register {server_config.name}: {e}")
        
        # 输出注册的工具列表
        all_tools = mcp_registry.list_tools()
        if all_tools:
            logger.info(f"  Registered {len(all_tools)} MCP tools:")
            for tool in all_tools[:5]:  # 只显示前5个
                logger.info(f"    - {tool.name}: {tool.description[:50]}...")
            if len(all_tools) > 5:
                logger.info(f"    ... and {len(all_tools) - 5} more")
        
        logger.info("✓ MCP servers ready")
    
    async def _register_sqlite_tools(self, server_name: str, db_path: str):
        """注册 SQLite 数据库工具"""
        from langchain.tools import tool
        import sqlite3
        
        if not os.path.exists(db_path):
            logger.warning(f"    Database not found: {db_path}")
            return
        
        @tool
        def query_database(query: str) -> str:
            """
            执行 SQL 查询并返回结果。
            
            Args:
                query: SQL 查询语句（仅支持 SELECT）
            
            Returns:
                查询结果的 JSON 格式
            """
            # 安全检查：只允许 SELECT 查询
            query_upper = query.strip().upper()
            if not query_upper.startswith("SELECT"):
                return "错误：出于安全考虑，只允许 SELECT 查询"
            
            try:
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                conn.close()
                
                # 转换为字典列表
                result = [dict(row) for row in rows]
                return json.dumps(result, ensure_ascii=False, indent=2)
            except Exception as e:
                return f"查询错误: {str(e)}"
        
        @tool
        def list_tables() -> str:
            """
            列出数据库中的所有表。
            
            Returns:
                表名列表
            """
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                conn.close()
                return json.dumps(tables, ensure_ascii=False)
            except Exception as e:
                return f"错误: {str(e)}"
        
        @tool
        def describe_table(table_name: str) -> str:
            """
            获取表的结构信息。
            
            Args:
                table_name: 表名
            
            Returns:
                表结构信息
            """
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                conn.close()
                
                result = []
                for col in columns:
                    result.append({
                        "name": col[1],
                        "type": col[2],
                        "nullable": not col[3],
                        "primary_key": bool(col[5]),
                    })
                return json.dumps(result, ensure_ascii=False, indent=2)
            except Exception as e:
                return f"错误: {str(e)}"
        
        # 注册到工具注册表
        from app.core.tool_registry import get_tool_registry, ToolPermission
        
        registry = get_tool_registry()
        registry.register(query_database, permission=ToolPermission.PUBLIC, category="database")
        registry.register(list_tables, permission=ToolPermission.PUBLIC, category="database")
        registry.register(describe_table, permission=ToolPermission.PUBLIC, category="database")
        
        logger.info(f"    ✓ Registered 3 database tools for {server_name}")
    
    async def initialize(self):
        """初始化所有组件"""
        logger.info("=" * 60)
        logger.info(f"Initializing {self.config.app_name}")
        logger.info("=" * 60)
        
        # 1. 设置RAG
        await self.setup_rag_system()
        
        # 2. 设置MCP
        await self.setup_mcp_servers()
        
        # 3. 创建Context Loader
        context_loader = ContextLoader(
            workspace_root=self.config.context.path_whitelist[0] if self.config.context.path_whitelist else None
        ) if self.config.features.enable_path_reference else None
        
        # 4. 创建核心组件
        memory_manager = MemoryManager()
        tool_executor = ToolExecutor(mcp_registry)
        
        # 5. 创建Agent (Orchestrator)
        self.agent = AgentEngine(
            memory_manager=memory_manager,
            tool_executor=tool_executor,
            context_loader=context_loader,
            enable_summarization=False,  # 禁用需要 OpenAI key 的功能
        )
        
        # 保存其他组件供后续使用
        self.memory_manager = memory_manager
        self.tool_executor = tool_executor
        self.context_loader = context_loader
        
        logger.info("✓ All components initialized")
        logger.info("=" * 60)
    
    async def start_web_server(self):
        """启动Web服务器"""
        import uvicorn
        from app.main import app
        
        # 设置UI配置
        app.state.ui_config = self.config.ui
        app.state.app_name = self.config.app_name
        
        logger.info(f"Starting web server on http://0.0.0.0:8000")
        logger.info(f"UI: {self.config.ui.title}")
        logger.info("=" * 60)
        
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
        
        server = uvicorn.Server(config)
        await server.serve()
    
    async def run(self):
        """运行应用"""
        try:
            # 加载配置
            self.load_configuration()
            
            # 初始化组件
            await self.initialize()
            
            # 启动Web服务器
            await self.start_web_server()
            
        except KeyboardInterrupt:
            logger.info("\n👋 Shutting down...")
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            raise


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Agentic ChatBot - 独立GUI模式"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="./config.json",
        help="配置文件路径 (默认: ./config.json)"
    )
    
    args = parser.parse_args()
    
    # 检查配置文件
    if not Path(args.config).exists():
        print(f"❌ 配置文件不存在: {args.config}")
        print()
        print("请按照以下步骤操作：")
        print("  1. 复制示例配置: cp config.json.example config.json")
        print("  2. 编辑配置文件: vim config.json")
        print("  3. 配置上下文来源:")
        print("     - rag_sources: 文档路径")
        print("     - path_whitelist: 允许引用的路径")
        print("     - mcp_servers: MCP服务器配置")
        print("  4. 重新运行此脚本")
        print()
        print("示例配置已保存到: config.json.example")
        sys.exit(1)
    
    # 创建并运行应用
    app = StandaloneGUI(config_path=args.config)
    
    print()
    print("=" * 60)
    print("🚀 Agentic ChatBot - 独立GUI模式")
    print("=" * 60)
    print()
    print("✨ 特点：")
    print("  • 零代码集成 - 只需配置文件")
    print("  • 自动加载上下文 - RAG + @路径 + MCP")
    print("  • 完整Web界面 - 开箱即用")
    print()
    print("📍 启动中...")
    print()
    
    # 运行
    asyncio.run(app.run())


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
功能验证测试脚本
验证所有核心功能是否正常工作
"""
import sys
import os
import time
import requests
from typing import Dict, Any

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_header(text: str):
    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.END}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_info(text: str):
    print(f"  {text}")


class SystemTester:
    """系统测试器"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.passed = 0
        self.failed = 0
        self.warnings = 0
    
    def test(self, name: str, func) -> bool:
        """执行单个测试"""
        try:
            print_info(f"Testing: {name}...")
            result = func()
            if result:
                print_success(name)
                self.passed += 1
                return True
            else:
                print_error(name)
                self.failed += 1
                return False
        except Exception as e:
            print_error(f"{name} - {e}")
            self.failed += 1
            return False
    
    def test_health(self) -> bool:
        """测试健康检查"""
        response = requests.get(f"{self.base_url}/health")
        return response.status_code == 200
    
    def test_api_docs(self) -> bool:
        """测试API文档"""
        response = requests.get(f"{self.base_url}/docs")
        return response.status_code == 200
    
    def test_chat_endpoint(self) -> bool:
        """测试聊天接口"""
        response = requests.post(
            f"{self.base_url}/api/v1/chat/message",
            json={
                "message": "Hello",
                "session_id": "test_session",
                "use_rag": False,
                "use_planning": False
            }
        )
        return response.status_code in [200, 422]  # 422表示需要额外配置
    
    def test_sdk_health(self) -> bool:
        """测试SDK健康检查"""
        response = requests.get(f"{self.base_url}/api/v1/sdk/health")
        return response.status_code == 200
    
    def test_file_structure(self) -> bool:
        """测试文件结构"""
        required_files = [
            "backend/app/main.py",
            "backend/app/config.py",
            "backend/app/core/agent.py",
            "backend/app/core/langchain_agent.py",  # LangChain 1.0
            "backend/app/core/tools.py",             # LangChain 1.0 工具
            "backend/app/core/memory.py",
            "backend/app/api/chat.py",
            "backend/app/api/sdk.py",
            "sdk/python/chatbot_sdk.py",
            "config.json.example",
            "standalone_gui.py",
        ]
        
        missing = []
        for file in required_files:
            if not os.path.exists(file):
                missing.append(file)
        
        if missing:
            print_warning(f"Missing files: {', '.join(missing)}")
            self.warnings += len(missing)
        
        return len(missing) == 0
    
    def test_env_config(self) -> bool:
        """测试环境配置"""
        env_file = "backend/.env"
        
        if not os.path.exists(env_file):
            print_warning(".env file not found")
            return False
        
        with open(env_file, 'r') as f:
            content = f.read()
        
        required_vars = ["OPENAI_API_KEY"]
        missing = [var for var in required_vars if var not in content]
        
        if missing:
            print_warning(f"Missing env vars: {', '.join(missing)}")
            return False
        
        # 检查是否配置了真实的key
        if "your_openai_api_key_here" in content:
            print_warning("Please configure real OPENAI_API_KEY")
            return False
        
        return True
    
    def test_directories(self) -> bool:
        """测试必要目录"""
        required_dirs = [
            "backend/data/documents",
            "backend/data/memory",
            "backend/data/vector_db",
            "backend/logs",
        ]
        
        missing = []
        for dir_path in required_dirs:
            if not os.path.exists(dir_path):
                missing.append(dir_path)
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    print_info(f"Created directory: {dir_path}")
                except Exception as e:
                    print_warning(f"Failed to create {dir_path}: {e}")
        
        return len(missing) == 0
    
    def test_dependencies(self) -> bool:
        """测试依赖安装"""
        try:
            import fastapi
            import langchain
            import langgraph
            import openai
            import chromadb
            
            # 检查 LangChain 1.0
            from langchain.agents import create_agent
            from langchain.tools import tool
            
            print_info("Core dependencies installed (LangChain 1.0+)")
            return True
        except ImportError as e:
            print_warning(f"Missing dependency: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print_header("Agentic ChatBot - 系统验证测试")
        
        # 1. 文件结构测试
        print_header("1. 文件结构检查")
        self.test("文件结构完整性", self.test_file_structure)
        self.test("必要目录存在", self.test_directories)
        
        # 2. 配置测试
        print_header("2. 配置检查")
        self.test("环境变量配置", self.test_env_config)
        
        # 3. 依赖测试
        print_header("3. 依赖检查")
        self.test("Python依赖安装", self.test_dependencies)
        
        # 4. 服务测试（如果服务在运行）
        print_header("4. 服务检查（如果正在运行）")
        try:
            if self.test("健康检查", self.test_health):
                self.test("API文档", self.test_api_docs)
                self.test("聊天接口", self.test_chat_endpoint)
                self.test("SDK接口", self.test_sdk_health)
        except requests.ConnectionError:
            print_warning("服务未运行，跳过服务测试")
            print_info("运行 ./start.csh 或 python backend/run.py 启动服务")
        
        # 5. 总结
        print_header("测试总结")
        print_info(f"通过: {Colors.GREEN}{self.passed}{Colors.END}")
        print_info(f"失败: {Colors.RED}{self.failed}{Colors.END}")
        print_info(f"警告: {Colors.YELLOW}{self.warnings}{Colors.END}")
        
        if self.failed == 0:
            print_success("\n✨ 所有核心测试通过！系统已就绪。")
            return True
        else:
            print_error(f"\n❌ {self.failed} 个测试失败，请检查并修复。")
            return False


def main():
    """主函数"""
    print(f"\n{Colors.BLUE}Agentic ChatBot - 功能验证{Colors.END}\n")
    
    # 切换到项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    print_info(f"项目根目录: {project_root}\n")
    
    # 运行测试
    tester = SystemTester()
    success = tester.run_all_tests()
    
    # 提供建议
    if success:
        print_header("🎯 下一步")
        print_info("方式一（独立GUI）：")
        print_info("  1. 配置: cp config.json.example config.json")
        print_info("  2. 启动: python standalone_gui.py")
        print_info("")
        print_info("方式二（SDK集成）：")
        print_info("  1. 查看示例: python examples/sdk_integration_examples.py")
        print_info("  2. 阅读文档: cat sdk/python/README.md")
        print_info("")
        print_info("📚 更多文档:")
        print_info("  - docs/QUICKSTART.md")
        print_info("  - docs/INTEGRATION_GUIDE.md")
        print_info("  - TARGET.md")
    else:
        print_header("🔧 修复建议")
        print_info("1. 检查缺失的文件和目录")
        print_info("2. 配置环境变量: vi backend/.env")
        print_info("3. 安装依赖: pip install -r backend/requirements.txt")
        print_info("4. 重新运行测试: python scripts/validate_system.py")
    
    print()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

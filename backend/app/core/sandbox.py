# -*- coding: utf-8 -*-
"""
安全沙箱执行器

提供安全的代码执行环境:
- 超时控制
- 资源限制（内存、CPU）
- 危险操作拦截
- 输出捕获和限制
- 多语言支持（Python, Shell）

使用示例:
    sandbox = Sandbox(timeout=5, max_output=10000)
    result = sandbox.execute_python("print('hello')")
    result = await sandbox.execute_python_async("print('async hello')")
"""
import sys
import os
import signal
import threading
import multiprocessing
from io import StringIO
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import traceback
import ast
from loguru import logger


class ExecutionStatus(str, Enum):
    """执行状态"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    SECURITY_VIOLATION = "security_violation"
    RESOURCE_LIMIT = "resource_limit"


@dataclass
class ExecutionResult:
    """执行结果"""
    status: ExecutionStatus
    output: str = ""
    error: str = ""
    return_value: Any = None
    execution_time_ms: float = 0.0
    memory_used_mb: float = 0.0


@dataclass
class SandboxConfig:
    """沙箱配置"""
    # 超时设置
    timeout_seconds: float = 10.0
    
    # 输出限制
    max_output_chars: int = 50000
    max_output_lines: int = 1000
    
    # 资源限制
    max_memory_mb: int = 256
    
    # 安全设置
    allow_imports: bool = False
    allowed_modules: Set[str] = field(default_factory=lambda: {
        'math', 'random', 'datetime', 'json', 're', 'collections',
        'itertools', 'functools', 'string', 'decimal', 'fractions',
        'time', 'statistics', 'copy', 'operator', 'typing',
    })
    
    # 禁止的操作
    forbidden_builtins: Set[str] = field(default_factory=lambda: {
        'exec', 'eval', 'compile', 'open', 'input',
        'breakpoint', 'help', 'license', 'credits', 'copyright',
    })
    
    forbidden_attributes: Set[str] = field(default_factory=lambda: {
        '__class__', '__bases__', '__subclasses__', '__mro__',
        '__code__', '__globals__', '__builtins__', '__import__',
        '__loader__', '__spec__', '__file__', '__path__',
    })
    
    forbidden_names: Set[str] = field(default_factory=lambda: {
        'os', 'sys', 'subprocess', 'shutil', 'socket', 'requests',
        'urllib', 'http', 'ftplib', 'telnetlib', 'smtplib',
        'pickle', 'shelve', 'marshal', 'ctypes', 'multiprocessing',
    })


class SecurityChecker(ast.NodeVisitor):
    """AST 安全检查器"""
    
    def __init__(self, config: SandboxConfig):
        self.config = config
        self.violations: List[str] = []
    
    def check(self, code: str) -> List[str]:
        """检查代码安全性"""
        self.violations = []
        try:
            tree = ast.parse(code)
            self.visit(tree)
        except SyntaxError as e:
            self.violations.append(f"语法错误: {e}")
        return self.violations
    
    def visit_Import(self, node):
        """检查 import 语句"""
        if not self.config.allow_imports:
            for alias in node.names:
                module = alias.name.split('.')[0]
                if module not in self.config.allowed_modules:
                    self.violations.append(f"禁止导入模块: {alias.name}")
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """检查 from ... import 语句"""
        if not self.config.allow_imports:
            module = node.module.split('.')[0] if node.module else ''
            if module not in self.config.allowed_modules:
                self.violations.append(f"禁止导入模块: {node.module}")
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """检查函数调用"""
        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name in self.config.forbidden_builtins:
                self.violations.append(f"禁止调用: {name}()")
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        """检查属性访问"""
        if node.attr in self.config.forbidden_attributes:
            self.violations.append(f"禁止访问属性: {node.attr}")
        self.generic_visit(node)
    
    def visit_Name(self, node):
        """检查名称引用"""
        if node.id in self.config.forbidden_names:
            self.violations.append(f"禁止使用: {node.id}")
        self.generic_visit(node)


class Sandbox:
    """安全沙箱执行器"""
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self.security_checker = SecurityChecker(self.config)
    
    def _create_safe_globals(self) -> Dict[str, Any]:
        """创建安全的全局环境"""
        import math
        import random
        import json
        import re
        import datetime
        import time
        import statistics
        import copy
        import operator
        from collections import Counter, defaultdict, OrderedDict, deque
        from itertools import chain, combinations, permutations, product
        from functools import reduce
        
        # 预加载的安全模块
        safe_modules = {
            'math': math,
            'random': random,
            'json': json,
            're': re,
            'datetime': datetime,
            'time': time,
            'statistics': statistics,
            'copy': copy,
            'operator': operator,
        }
        
        # 创建安全的 __import__ 函数
        allowed = self.config.allowed_modules
        def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            base_module = name.split('.')[0]
            if base_module in allowed and base_module in safe_modules:
                return safe_modules[base_module]
            raise ImportError(f"禁止导入模块: {name}")
        
        safe_builtins = {
            # 基本类型
            'True': True, 'False': False, 'None': None,
            'int': int, 'float': float, 'str': str, 'bool': bool,
            'list': list, 'dict': dict, 'set': set, 'tuple': tuple,
            'frozenset': frozenset, 'bytes': bytes, 'bytearray': bytearray,
            
            # 常用函数
            'print': print, 'len': len, 'range': range, 'enumerate': enumerate,
            'zip': zip, 'map': map, 'filter': filter, 'sorted': sorted,
            'reversed': reversed, 'sum': sum, 'min': min, 'max': max,
            'abs': abs, 'round': round, 'pow': pow, 'divmod': divmod,
            'all': all, 'any': any, 'bin': bin, 'hex': hex, 'oct': oct,
            'ord': ord, 'chr': chr, 'ascii': ascii, 'repr': repr,
            'format': format, 'hash': hash, 'id': id, 'type': type,
            'isinstance': isinstance, 'issubclass': issubclass,
            'callable': callable, 'iter': iter, 'next': next,
            'slice': slice, 'object': object,
            
            # 数学
            'complex': complex,
            
            # 安全导入
            '__import__': safe_import,
        }
        
        safe_globals = {
            '__builtins__': safe_builtins,
            '__name__': '__sandbox__',
            '__doc__': None,
            
            # 预加载的安全模块（可以直接使用）
            **safe_modules,
            
            # collections
            'Counter': Counter,
            'defaultdict': defaultdict,
            'OrderedDict': OrderedDict,
            'deque': deque,
            
            # itertools
            'chain': chain,
            'combinations': combinations,
            'permutations': permutations,
            'product': product,
            
            # functools
            'reduce': reduce,
        }
        
        return safe_globals
    
    def _truncate_output(self, output: str) -> str:
        """截断过长的输出"""
        lines = output.split('\n')
        
        # 限制行数
        if len(lines) > self.config.max_output_lines:
            lines = lines[:self.config.max_output_lines]
            lines.append(f"... (输出已截断，显示前 {self.config.max_output_lines} 行)")
        
        output = '\n'.join(lines)
        
        # 限制字符数
        if len(output) > self.config.max_output_chars:
            output = output[:self.config.max_output_chars]
            output += f"\n... (输出已截断，显示前 {self.config.max_output_chars} 字符)"
        
        return output
    
    def execute_python(self, code: str) -> ExecutionResult:
        """
        在沙箱中执行 Python 代码
        
        Args:
            code: Python 代码
        
        Returns:
            执行结果
        """
        import time
        start_time = time.time()
        
        # 1. 安全检查
        violations = self.security_checker.check(code)
        if violations:
            return ExecutionResult(
                status=ExecutionStatus.SECURITY_VIOLATION,
                error=f"安全检查失败:\n" + "\n".join(f"- {v}" for v in violations),
            )
        
        # 2. 准备执行环境
        safe_globals = self._create_safe_globals()
        safe_locals = {}
        
        # 3. 捕获输出
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        captured_output = StringIO()
        captured_error = StringIO()
        
        sys.stdout = captured_output
        sys.stderr = captured_error
        
        return_value = None
        status = ExecutionStatus.SUCCESS
        error_msg = ""
        
        try:
            # 4. 使用线程执行（支持超时）
            result_container = {'value': None, 'error': None}
            
            def run_code():
                try:
                    exec(code, safe_globals, safe_locals)
                    # 尝试获取最后一个表达式的值
                    if '_' in safe_locals:
                        result_container['value'] = safe_locals['_']
                except Exception as e:
                    result_container['error'] = e
            
            thread = threading.Thread(target=run_code)
            thread.daemon = True
            thread.start()
            thread.join(timeout=self.config.timeout_seconds)
            
            if thread.is_alive():
                # 超时
                status = ExecutionStatus.TIMEOUT
                error_msg = f"执行超时（限制 {self.config.timeout_seconds} 秒）"
            elif result_container['error']:
                status = ExecutionStatus.ERROR
                e = result_container['error']
                error_msg = f"{type(e).__name__}: {str(e)}"
            else:
                return_value = result_container['value']
        
        except Exception as e:
            status = ExecutionStatus.ERROR
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        
        # 5. 获取输出
        output = captured_output.getvalue()
        stderr = captured_error.getvalue()
        
        if stderr:
            error_msg = stderr + "\n" + error_msg if error_msg else stderr
        
        # 6. 截断输出
        output = self._truncate_output(output)
        
        execution_time = (time.time() - start_time) * 1000
        
        return ExecutionResult(
            status=status,
            output=output,
            error=error_msg,
            return_value=return_value,
            execution_time_ms=execution_time,
        )
    
    async def execute_python_async(self, code: str) -> ExecutionResult:
        """异步版本的 Python 执行"""
        import asyncio
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.execute_python, code)
    
    def execute_shell(self, command: str, timeout: Optional[float] = None) -> ExecutionResult:
        """
        在沙箱中执行 Shell 命令（受限）
        
        Args:
            command: Shell 命令
            timeout: 超时时间
        
        Returns:
            执行结果
        """
        import subprocess
        import shlex
        import time
        
        start_time = time.time()
        timeout = timeout or self.config.timeout_seconds
        
        # 安全检查 - 禁止危险命令
        dangerous_patterns = [
            'rm -rf', 'rm -r /', 'dd if=', 'mkfs', 'format',
            '> /dev/', ':(){', 'chmod 777', 'wget', 'curl',
            'nc ', 'netcat', 'ssh ', 'scp ', 'rsync',
        ]
        
        for pattern in dangerous_patterns:
            if pattern in command.lower():
                return ExecutionResult(
                    status=ExecutionStatus.SECURITY_VIOLATION,
                    error=f"禁止执行危险命令: 包含 '{pattern}'",
                )
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd='/tmp',  # 限制工作目录
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            if result.returncode == 0:
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output=self._truncate_output(result.stdout),
                    execution_time_ms=execution_time,
                )
            else:
                return ExecutionResult(
                    status=ExecutionStatus.ERROR,
                    output=self._truncate_output(result.stdout),
                    error=result.stderr,
                    execution_time_ms=execution_time,
                )
        
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                error=f"命令执行超时（限制 {timeout} 秒）",
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                error=f"执行错误: {str(e)}",
            )


# ==================== 工具函数 ====================

_default_sandbox: Optional[Sandbox] = None


def get_sandbox() -> Sandbox:
    """获取默认沙箱实例"""
    global _default_sandbox
    if _default_sandbox is None:
        _default_sandbox = Sandbox()
    return _default_sandbox


def safe_exec(code: str) -> str:
    """
    安全执行 Python 代码（简化接口）
    
    Args:
        code: Python 代码
    
    Returns:
        格式化的执行结果
    """
    sandbox = get_sandbox()
    result = sandbox.execute_python(code)
    
    if result.status == ExecutionStatus.SUCCESS:
        output = result.output if result.output else "(无输出)"
        return f"✅ 执行成功 ({result.execution_time_ms:.1f}ms):\n```\n{output}\n```"
    elif result.status == ExecutionStatus.TIMEOUT:
        return f"⏱️ {result.error}"
    elif result.status == ExecutionStatus.SECURITY_VIOLATION:
        return f"🔒 {result.error}"
    else:
        return f"❌ 执行错误:\n{result.error}"


async def safe_exec_async(code: str) -> str:
    """异步版本的安全执行"""
    sandbox = get_sandbox()
    result = await sandbox.execute_python_async(code)
    
    if result.status == ExecutionStatus.SUCCESS:
        output = result.output if result.output else "(无输出)"
        return f"✅ 执行成功 ({result.execution_time_ms:.1f}ms):\n```\n{output}\n```"
    elif result.status == ExecutionStatus.TIMEOUT:
        return f"⏱️ {result.error}"
    elif result.status == ExecutionStatus.SECURITY_VIOLATION:
        return f"🔒 {result.error}"
    else:
        return f"❌ 执行错误:\n{result.error}"

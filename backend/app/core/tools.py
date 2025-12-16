# -*- coding: utf-8 -*-
"""
LangChain 1.0 工具定义

使用 @tool 装饰器定义工具，支持:
- 自动生成工具描述
- 参数类型验证
- 异步执行
- 运行时上下文注入

文档: https://docs.langchain.com/oss/python/langchain/tools
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from langchain.tools import tool, ToolRuntime
from loguru import logger


# ==================== 基础工具 ====================

@tool
def calculator(expression: str) -> str:
    """
    计算数学表达式。
    
    支持基本运算: +, -, *, /, **, (, )
    
    Args:
        expression: 数学表达式，如 "2 + 3 * 4" 或 "(10 + 5) / 3"
    
    Returns:
        计算结果字符串
    
    Examples:
        >>> calculator("2 + 3 * 4")
        "✅ 计算结果: 2 + 3 * 4 = 14"
    """
    try:
        # 安全的数学表达式计算
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "❌ 错误：表达式包含不允许的字符。只支持数字和基本运算符"
        
        result = eval(expression)
        return f"✅ 计算结果: {expression} = {result}"
    except ZeroDivisionError:
        return "❌ 错误：除数不能为零"
    except Exception as e:
        return f"❌ 计算错误: {str(e)}"


@tool
def get_current_time() -> str:
    """
    获取当前时间。
    
    Returns:
        格式化的当前时间字符串，包含年月日时分秒和星期
    """
    now = datetime.now()
    weekdays = ['一', '二', '三', '四', '五', '六', '日']
    return f"🕐 当前时间: {now.strftime('%Y年%m月%d日 %H:%M:%S')} (星期{weekdays[now.weekday()]})"


@tool
def get_current_date() -> str:
    """
    获取当前日期。
    
    Returns:
        格式化的当前日期字符串
    """
    now = datetime.now()
    return f"📅 当前日期: {now.strftime('%Y年%m月%d日')}"


# ==================== 文本处理工具 ====================

@tool
def word_count(text: str) -> str:
    """
    统计文本的字数、词数和字符数。
    
    Args:
        text: 要统计的文本
    
    Returns:
        统计结果
    """
    char_count = len(text)
    word_count = len(text.split())
    
    # 中文字符统计
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    
    return f"""📊 文本统计:
- 总字符数: {char_count}
- 英文单词数: {word_count}
- 中文字符数: {chinese_chars}"""


@tool
def text_to_uppercase(text: str) -> str:
    """
    将文本转换为大写。
    
    Args:
        text: 要转换的文本
    
    Returns:
        大写文本
    """
    return text.upper()


@tool
def text_to_lowercase(text: str) -> str:
    """
    将文本转换为小写。
    
    Args:
        text: 要转换的文本
    
    Returns:
        小写文本
    """
    return text.lower()


# ==================== 数据格式化工具 ====================

@tool
def format_json(json_string: str) -> str:
    """
    格式化 JSON 字符串，使其更易读。
    
    Args:
        json_string: JSON 字符串
    
    Returns:
        格式化后的 JSON 字符串
    """
    import json
    try:
        data = json.loads(json_string)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return f"❌ JSON 解析错误: {str(e)}"


@tool
def validate_json(json_string: str) -> str:
    """
    验证 JSON 字符串是否有效。
    
    Args:
        json_string: 要验证的 JSON 字符串
    
    Returns:
        验证结果
    """
    import json
    try:
        json.loads(json_string)
        return "✅ JSON 格式有效"
    except json.JSONDecodeError as e:
        return f"❌ JSON 格式无效: {str(e)}"


# ==================== 代码执行工具 ====================

@tool
def run_python_code(code: str) -> str:
    """
    执行 Python 代码并返回结果。
    
    ⚠️ 安全警告: 此工具在沙盒中执行代码，限制了危险操作。
    
    Args:
        code: 要执行的 Python 代码
    
    Returns:
        执行结果或错误信息
    """
    import sys
    from io import StringIO
    
    # 限制危险操作
    forbidden = ['import os', 'import subprocess', 'import shutil', 
                 'open(', '__import__', 'exec(', 'eval(', 'compile(']
    for f in forbidden:
        if f in code:
            return f"❌ 安全限制: 禁止使用 '{f}'"
    
    # 捕获输出
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    
    try:
        # 创建受限的全局环境
        safe_globals = {
            '__builtins__': {
                'print': print, 'len': len, 'range': range, 'sum': sum,
                'min': min, 'max': max, 'abs': abs, 'round': round,
                'list': list, 'dict': dict, 'set': set, 'tuple': tuple,
                'str': str, 'int': int, 'float': float, 'bool': bool,
                'sorted': sorted, 'reversed': reversed, 'enumerate': enumerate,
                'zip': zip, 'map': map, 'filter': filter,
            }
        }
        
        exec(code, safe_globals)
        output = sys.stdout.getvalue()
        
        return f"✅ 执行成功:\n```\n{output if output else '(无输出)'}\n```"
    except Exception as e:
        return f"❌ 执行错误: {type(e).__name__}: {str(e)}"
    finally:
        sys.stdout = old_stdout


@tool
def read_file_content(file_path: str, max_lines: int = 100) -> str:
    """
    读取文件内容。
    
    Args:
        file_path: 文件路径
        max_lines: 最大读取行数（默认 100）
    
    Returns:
        文件内容或错误信息
    """
    import os
    
    # 安全检查
    if '..' in file_path or file_path.startswith('/'):
        return "❌ 安全限制: 不允许访问上级目录或绝对路径"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()[:max_lines]
            content = ''.join(lines)
            
            if len(lines) == max_lines:
                content += f"\n... (文件已截断，显示前 {max_lines} 行)"
            
            return f"📄 文件内容 ({file_path}):\n```\n{content}\n```"
    except FileNotFoundError:
        return f"❌ 文件不存在: {file_path}"
    except Exception as e:
        return f"❌ 读取错误: {str(e)}"


# ==================== 搜索工具（示例）====================

@tool
def search_web(query: str) -> str:
    """
    搜索网络信息（模拟）。
    
    注意: 这是一个模拟工具，实际使用需要集成真实的搜索 API。
    
    Args:
        query: 搜索查询
    
    Returns:
        搜索结果摘要
    """
    # TODO: 实现真实的网络搜索
    return f"🔍 搜索 '{query}' 的结果：暂无真实搜索结果。这是一个模拟工具，请集成真实的搜索 API。"


@tool
def search_knowledge_base(query: str) -> str:
    """
    搜索内部知识库（模拟）。
    
    Args:
        query: 搜索查询
    
    Returns:
        知识库搜索结果
    """
    # TODO: 实现 RAG 检索
    return f"📚 知识库搜索 '{query}': 暂无结果。请确保已配置 RAG 知识库。"


# ==================== 带上下文的工具 ====================

@dataclass
class UserContext:
    """用户上下文"""
    user_id: str = ""
    session_id: str = ""
    language: str = "zh-CN"


@tool
def get_user_info(runtime: ToolRuntime[UserContext]) -> str:
    """
    获取当前用户信息。
    
    这是一个使用运行时上下文的工具示例。
    
    Args:
        runtime: 运行时上下文，包含用户信息
    
    Returns:
        用户信息
    """
    ctx = runtime.context
    return f"""👤 当前用户信息:
- 用户 ID: {ctx.user_id or '未知'}
- 会话 ID: {ctx.session_id or '未知'}
- 语言: {ctx.language or 'zh-CN'}"""


# ==================== 工具集合 ====================

def get_builtin_tools() -> List:
    """
    获取所有内置工具
    
    Returns:
        工具列表
    """
    return [
        calculator,
        get_current_time,
        get_current_date,
        word_count,
        text_to_uppercase,
        text_to_lowercase,
        format_json,
        validate_json,
        run_python_code,
        read_file_content,
        search_web,
        search_knowledge_base,
    ]


def get_basic_tools() -> List:
    """
    获取基础工具集（最小集合）
    
    Returns:
        基础工具列表
    """
    return [
        calculator,
        get_current_time,
        get_current_date,
        run_python_code,
    ]


# ==================== 工具装饰器帮助函数 ====================

def create_tool_from_function(
    func,
    name: Optional[str] = None,
    description: Optional[str] = None,
):
    """
    从普通函数创建 LangChain 工具
    
    Args:
        func: 函数
        name: 工具名称（可选，默认使用函数名）
        description: 工具描述（可选，默认使用 docstring）
    
    Returns:
        LangChain 工具
    """
    from langchain.tools import StructuredTool
    
    return StructuredTool.from_function(
        func=func,
        name=name or func.__name__,
        description=description or func.__doc__ or "无描述",
    )

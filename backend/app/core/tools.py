# -*- coding: utf-8 -*-
"""
LangChain 1.0 工具定义

核心工具集 - 只保留真正实用的工具
"""
from typing import Optional, List
from datetime import datetime
from langchain.tools import tool
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
    """
    try:
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "❌ 错误：表达式包含不允许的字符"
        
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
        格式化的当前时间字符串
    """
    now = datetime.now()
    weekdays = ['一', '二', '三', '四', '五', '六', '日']
    return f"🕐 当前时间: {now.strftime('%Y年%m月%d日 %H:%M:%S')} (星期{weekdays[now.weekday()]})"


# ==================== Python 代码执行 ====================

@tool
def run_python_code(code: str) -> str:
    """
    执行 Python 代码并返回结果。
    
    ⚠️ 在沙盒中执行，有安全限制。
    
    Args:
        code: 要执行的 Python 代码
    
    Returns:
        执行结果或错误信息
    """
    from .sandbox import safe_exec
    return safe_exec(code)


# ==================== 知识库搜索 ====================

@tool
async def search_knowledge_base(query: str, top_k: int = 5) -> str:
    """
    搜索内部知识库 (RAG)。
    
    Args:
        query: 搜索查询
        top_k: 返回结果数量
    
    Returns:
        知识库搜索结果
    """
    try:
        from ..rag import retriever
        
        results = await retriever.retrieve(query=query, top_k=top_k)
        
        if not results:
            return f"📚 知识库搜索 '{query}': 未找到相关结果。"
        
        output_parts = [f"📚 知识库搜索 '{query}' 找到 {len(results)} 条结果:\n"]
        
        for i, result in enumerate(results, 1):
            content = result.get("content", "")[:500]
            source = result.get("source", "未知")
            score = result.get("score", 0)
            
            output_parts.append(f"\n---\n**结果 {i}** (相似度: {score:.2f})")
            output_parts.append(f"\n📄 来源: {source}")
            output_parts.append(f"\n\n{content}")
        
        return "".join(output_parts)
        
    except Exception as e:
        logger.error(f"Knowledge base search failed: {e}")
        return f"📚 知识库搜索出错: {str(e)}"


# ==================== 工具集合 ====================

from .practical_tools import get_practical_tools

def get_builtin_tools() -> List:
    """
    获取所有内置工具
    
    Returns:
        工具列表
    """
    # 基础工具
    basic = [
        calculator,
        get_current_time,
        run_python_code,
        search_knowledge_base,
    ]
    
    # 实用工具（shell、文件、网页等）
    practical = get_practical_tools()
    
    return basic + practical


def get_basic_tools() -> List:
    """
    获取基础工具集（最小集合）
    """
    from .practical_tools import shell_execute, file_read_enhanced, list_directory
    
    return [
        calculator,
        get_current_time,
        shell_execute,
        file_read_enhanced,
        list_directory,
    ]


def get_extended_tools() -> List:
    """
    获取扩展工具集（空，已整合到 practical_tools）
    """
    return []


# ==================== 导出 ====================

__all__ = [
    "calculator",
    "get_current_time",
    "run_python_code",
    "search_knowledge_base",
    "get_builtin_tools",
    "get_basic_tools",
    "get_extended_tools",
]

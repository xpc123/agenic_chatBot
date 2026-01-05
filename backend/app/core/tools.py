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
    
    ⚠️ 安全警告: 此工具在增强沙盒中执行代码，有以下限制:
    - 超时限制: 10 秒
    - 禁止危险操作（文件、网络、系统调用）
    - 输出限制: 最多 50000 字符
    
    支持的模块: math, random, datetime, json, re, collections, itertools
    
    Args:
        code: 要执行的 Python 代码
    
    Returns:
        执行结果或错误信息
    
    Examples:
        >>> run_python_code("print([i**2 for i in range(10)])")
        "✅ 执行成功: [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]"
    """
    from backend.app.core.sandbox import safe_exec
    return safe_exec(code)


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
async def search_knowledge_base(query: str, top_k: int = 5) -> str:
    """
    搜索内部知识库。
    
    使用 RAG 系统检索与查询相关的文档内容。
    
    Args:
        query: 搜索查询
        top_k: 返回结果数量（默认5条）
    
    Returns:
        知识库搜索结果
    """
    try:
        from ..rag import retriever
        
        # 执行检索
        results = await retriever.retrieve(
            query=query,
            top_k=top_k,
        )
        
        if not results:
            return f"📚 知识库搜索 '{query}': 未找到相关结果。"
        
        # 格式化结果
        output_parts = [f"📚 知识库搜索 '{query}' 找到 {len(results)} 条结果:\n"]
        
        for i, result in enumerate(results, 1):
            content = result.get("content", "")
            source = result.get("source", result.get("metadata", {}).get("source", "未知来源"))
            score = result.get("score", 0)
            citation = result.get("citation", "")
            
            # 截断过长内容
            if len(content) > 500:
                content = content[:500] + "..."
            
            output_parts.append(f"\n---\n**结果 {i}** (相似度: {score:.2f})")
            if source:
                output_parts.append(f"\n📄 来源: {source}")
            if citation:
                output_parts.append(f"\n🔗 引用: {citation}")
            output_parts.append(f"\n\n{content}")
        
        return "".join(output_parts)
        
    except Exception as e:
        logger.error(f"Knowledge base search failed: {e}")
        return f"📚 知识库搜索出错: {str(e)}"


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

# 导入实用工具
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
        get_current_date,
        run_python_code,
        search_knowledge_base,
    ]
    
    # 实用工具（shell、文件、网页等）
    practical = get_practical_tools()
    
    return basic + practical


def get_basic_tools() -> List:
    """
    获取基础工具集（最小集合）
    
    Returns:
        基础工具列表
    """
    from .practical_tools import shell_execute, file_read_enhanced, list_directory
    
    return [
        calculator,
        get_current_time,
        shell_execute,
        file_read_enhanced,
        list_directory,
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


# ==================== HTTP 请求工具 ====================

@tool
def http_request(url: str, method: str = "GET", headers: str = "", body: str = "") -> str:
    """
    发送 HTTP 请求并返回响应。
    
    Args:
        url: 请求 URL
        method: 请求方法 (GET, POST, PUT, DELETE)
        headers: 请求头 (JSON 格式字符串，可选)
        body: 请求体 (JSON 格式字符串，可选)
    
    Returns:
        响应内容或错误信息
    
    Examples:
        >>> http_request("https://api.github.com", "GET")
        "✅ 响应 (200): {...}"
    """
    import httpx
    import json as json_module
    
    try:
        # 解析 headers
        parsed_headers = {}
        if headers:
            try:
                parsed_headers = json_module.loads(headers)
            except:
                return "❌ headers 格式错误，请使用 JSON 格式"
        
        # 解析 body
        parsed_body = None
        if body:
            try:
                parsed_body = json_module.loads(body)
            except:
                parsed_body = body  # 作为原始字符串
        
        # 发送请求
        with httpx.Client(timeout=30.0) as client:
            response = client.request(
                method=method.upper(),
                url=url,
                headers=parsed_headers,
                json=parsed_body if isinstance(parsed_body, dict) else None,
                content=parsed_body if isinstance(parsed_body, str) else None,
            )
        
        # 处理响应
        status = response.status_code
        content_type = response.headers.get("content-type", "")
        
        if "json" in content_type:
            try:
                result = json_module.dumps(response.json(), ensure_ascii=False, indent=2)
            except:
                result = response.text
        else:
            result = response.text
        
        # 截断过长的响应
        if len(result) > 5000:
            result = result[:5000] + "\n... (响应已截断)"
        
        return f"✅ HTTP {status}:\n```\n{result}\n```"
    
    except httpx.TimeoutException:
        return f"❌ 请求超时: {url}"
    except httpx.RequestError as e:
        return f"❌ 请求错误: {str(e)}"
    except Exception as e:
        return f"❌ 错误: {str(e)}"


@tool  
def url_fetch(url: str) -> str:
    """
    获取网页内容（简化版）。
    
    自动处理编码，提取文本内容。
    
    Args:
        url: 网页 URL
    
    Returns:
        网页文本内容
    """
    import httpx
    from html.parser import HTMLParser
    
    class TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.text_parts = []
            self.skip_tags = {'script', 'style', 'head', 'title', 'meta', 'link'}
            self.current_tag = None
            
        def handle_starttag(self, tag, attrs):
            self.current_tag = tag
            
        def handle_endtag(self, tag):
            self.current_tag = None
            
        def handle_data(self, data):
            if self.current_tag not in self.skip_tags:
                text = data.strip()
                if text:
                    self.text_parts.append(text)
        
        def get_text(self):
            return '\n'.join(self.text_parts)
    
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; ChatBot/1.0)"
            })
            response.raise_for_status()
        
        content_type = response.headers.get("content-type", "")
        
        if "html" in content_type:
            parser = TextExtractor()
            parser.feed(response.text)
            text = parser.get_text()
        else:
            text = response.text
        
        # 截断
        if len(text) > 10000:
            text = text[:10000] + "\n... (内容已截断)"
        
        return f"📄 网页内容:\n{text}"
    
    except Exception as e:
        return f"❌ 获取失败: {str(e)}"


# ==================== 系统信息工具 ====================

@tool
def get_system_info() -> str:
    """
    获取系统基本信息。
    
    Returns:
        系统信息摘要
    """
    import platform
    
    info = {
        "系统": platform.system(),
        "版本": platform.release(),
        "架构": platform.machine(),
        "Python": platform.python_version(),
        "处理器": platform.processor() or "未知",
    }
    
    result = "💻 系统信息:\n"
    for key, value in info.items():
        result += f"- {key}: {value}\n"
    
    return result


# ==================== 扩展工具集合 ====================

def get_extended_tools() -> List:
    """
    获取扩展工具集（仅包含新增的 HTTP 和系统工具）
    
    注意：不包含已在 get_builtin_tools 中的工具，避免重复注册
    
    Returns:
        扩展工具列表
    """
    return [
        # HTTP 工具（新增）
        http_request,
        url_fetch,
        
        # 系统工具（新增）
        get_system_info,
    ]

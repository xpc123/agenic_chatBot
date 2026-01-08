# -*- coding: utf-8 -*-
"""
实用工具集 - Practical Tools

真正有用的内置工具，让 AI 助手能够完成实际任务
"""
import os
import subprocess
import asyncio
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from langchain.tools import tool
from loguru import logger

from ..config import settings


# ==================== 1. Shell 命令执行 ====================

@tool
def shell_execute(command: str, working_dir: str = "", timeout: int = 60) -> str:
    """
    执行 Shell 命令并返回结果。
    
    ⚠️ 安全提示: 此工具可执行任意 shell 命令，请谨慎使用。
    
    Args:
        command: 要执行的 shell 命令
        working_dir: 工作目录（可选，默认为当前目录）
        timeout: 超时时间（秒），默认 60 秒
    
    Returns:
        命令执行结果（stdout + stderr）
    
    Examples:
        >>> shell_execute("ls -la")
        >>> shell_execute("pwd")
        >>> shell_execute("cat /etc/os-release")
    """
    try:
        cwd = working_dir if working_dir else None
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[stderr]: {result.stderr}"
        
        exit_code = result.returncode
        
        if exit_code == 0:
            return f"✅ 命令执行成功 (exit code: {exit_code})\n\n```\n{output.strip()}\n```"
        else:
            return f"⚠️ 命令执行完成 (exit code: {exit_code})\n\n```\n{output.strip()}\n```"
            
    except subprocess.TimeoutExpired:
        return f"❌ 命令执行超时 ({timeout}秒)"
    except Exception as e:
        return f"❌ 命令执行失败: {str(e)}"


# ==================== 2. 文件写入 ====================

@tool
def file_write(file_path: str, content: str, mode: str = "write") -> str:
    """
    写入内容到文件。
    
    Args:
        file_path: 文件路径（相对或绝对路径）
        content: 要写入的内容
        mode: 写入模式 - "write" 覆盖写入, "append" 追加写入
    
    Returns:
        操作结果
    
    Examples:
        >>> file_write("test.txt", "Hello World")
        >>> file_write("log.txt", "New log entry", mode="append")
    """
    try:
        path = Path(file_path)
        
        # 确保父目录存在
        path.parent.mkdir(parents=True, exist_ok=True)
        
        write_mode = "w" if mode == "write" else "a"
        
        with open(path, write_mode, encoding="utf-8") as f:
            f.write(content)
            if mode == "append" and not content.endswith("\n"):
                f.write("\n")
        
        file_size = path.stat().st_size
        action = "写入" if mode == "write" else "追加"
        
        return f"✅ 文件{action}成功\n- 路径: {path.absolute()}\n- 大小: {file_size} bytes"
        
    except PermissionError:
        return f"❌ 权限不足，无法写入: {file_path}"
    except Exception as e:
        return f"❌ 文件写入失败: {str(e)}"


# ==================== 3. 增强版文件读取 ====================

@tool
def file_read_enhanced(
    file_path: str, 
    start_line: int = 0, 
    end_line: int = 0,
    encoding: str = "utf-8"
) -> str:
    """
    读取文件内容（增强版）。
    
    支持:
    - 读取指定行范围
    - 自动检测编码
    - 大文件分块读取
    
    Args:
        file_path: 文件路径
        start_line: 起始行号（从 1 开始，0 表示从头开始）
        end_line: 结束行号（0 表示读取到末尾）
        encoding: 文件编码，默认 utf-8
    
    Returns:
        文件内容
    
    Examples:
        >>> file_read_enhanced("config.py")
        >>> file_read_enhanced("large_file.log", start_line=100, end_line=200)
    """
    try:
        path = Path(file_path)
        
        if not path.exists():
            return f"❌ 文件不存在: {file_path}"
        
        file_size = path.stat().st_size
        
        # 文件信息
        info = f"📄 文件: {path.name}\n- 路径: {path.absolute()}\n- 大小: {file_size:,} bytes\n"
        
        with open(path, "r", encoding=encoding, errors="replace") as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        info += f"- 总行数: {total_lines}\n"
        
        # 处理行范围
        start = max(0, start_line - 1) if start_line > 0 else 0
        end = end_line if end_line > 0 else total_lines
        
        selected_lines = lines[start:end]
        
        if start > 0 or end < total_lines:
            info += f"- 显示行: {start + 1} - {min(end, total_lines)}\n"
        
        content = "".join(selected_lines)
        
        # 截断过长内容
        max_chars = 50000
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n... (内容已截断，总共 {len(content)} 字符)"
        
        return f"{info}\n```\n{content}\n```"
        
    except UnicodeDecodeError:
        return f"❌ 编码错误，请尝试指定其他编码 (如 encoding='gbk')"
    except Exception as e:
        return f"❌ 文件读取失败: {str(e)}"


# ==================== 4. 网页抓取 ====================

@tool
async def web_fetch(url: str, extract_text: bool = True) -> str:
    """
    抓取网页内容。
    
    Args:
        url: 网页 URL
        extract_text: 是否只提取文本（去除 HTML 标签）
    
    Returns:
        网页内容
    
    Examples:
        >>> web_fetch("https://example.com")
        >>> web_fetch("https://news.ycombinator.com", extract_text=True)
    """
    import httpx
    from html.parser import HTMLParser
    
    class TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.text_parts = []
            self.skip_tags = {'script', 'style', 'head', 'title', 'meta', 'link', 'noscript'}
            self.current_tag = None
            
        def handle_starttag(self, tag, attrs):
            self.current_tag = tag
            
        def handle_endtag(self, tag):
            if tag in ('p', 'div', 'br', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
                self.text_parts.append('\n')
            self.current_tag = None
            
        def handle_data(self, data):
            if self.current_tag not in self.skip_tags:
                text = data.strip()
                if text:
                    self.text_parts.append(text + ' ')
        
        def get_text(self):
            return ''.join(self.text_parts).strip()
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; AgenticBot/1.0)"
            })
            response.raise_for_status()
        
        content_type = response.headers.get("content-type", "")
        
        if extract_text and "html" in content_type:
            parser = TextExtractor()
            parser.feed(response.text)
            text = parser.get_text()
        else:
            text = response.text
        
        # 截断
        max_chars = 20000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n... (内容已截断)"
        
        return f"🌐 网页内容 ({url})\n\n{text}"
        
    except httpx.TimeoutException:
        return f"❌ 请求超时: {url}"
    except httpx.HTTPStatusError as e:
        return f"❌ HTTP 错误 {e.response.status_code}: {url}"
    except Exception as e:
        return f"❌ 网页抓取失败: {str(e)}"


# ==================== 5. 进程管理 ====================

@tool
def process_list(filter_name: str = "") -> str:
    """
    列出当前运行的进程。
    
    Args:
        filter_name: 过滤进程名（可选）
    
    Returns:
        进程列表
    
    Examples:
        >>> process_list()
        >>> process_list("python")
        >>> process_list("virtuoso")
    """
    try:
        if filter_name:
            cmd = f"ps aux | grep -i '{filter_name}' | grep -v grep"
        else:
            cmd = "ps aux --sort=-%mem | head -20"
        
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        output = result.stdout.strip()
        
        if not output:
            return f"📋 没有找到匹配的进程: {filter_name}"
        
        return f"📋 进程列表:\n```\n{output}\n```"
        
    except Exception as e:
        return f"❌ 获取进程列表失败: {str(e)}"


# ==================== 6. 环境信息 ====================

@tool
def env_info() -> str:
    """
    获取当前环境信息。
    
    Returns:
        环境信息摘要
    """
    import platform
    import sys
    
    info = {
        "操作系统": f"{platform.system()} {platform.release()}",
        "主机名": platform.node(),
        "架构": platform.machine(),
        "Python": sys.version.split()[0],
        "当前目录": os.getcwd(),
        "用户": os.environ.get("USER", "unknown"),
        "HOME": os.environ.get("HOME", "unknown"),
        "SHELL": os.environ.get("SHELL", "unknown"),
    }
    
    result = "💻 环境信息:\n"
    for key, value in info.items():
        result += f"- {key}: {value}\n"
    
    return result


# ==================== 7. 目录操作 ====================

@tool
def list_directory(
    path: str = ".", 
    pattern: str = "", 
    recursive: bool = False,
    show_hidden: bool = False
) -> str:
    """
    列出目录内容。
    
    Args:
        path: 目录路径，默认当前目录
        pattern: 文件名过滤模式（如 "*.py"）
        recursive: 是否递归列出子目录
        show_hidden: 是否显示隐藏文件
    
    Returns:
        目录内容列表
    
    Examples:
        >>> list_directory("/home/user/project")
        >>> list_directory(".", pattern="*.py", recursive=True)
    """
    try:
        dir_path = Path(path)
        
        if not dir_path.exists():
            return f"❌ 目录不存在: {path}"
        
        if not dir_path.is_dir():
            return f"❌ 不是目录: {path}"
        
        if recursive:
            if pattern:
                items = list(dir_path.rglob(pattern))
            else:
                items = list(dir_path.rglob("*"))
        else:
            if pattern:
                items = list(dir_path.glob(pattern))
            else:
                items = list(dir_path.iterdir())
        
        # 过滤隐藏文件
        if not show_hidden:
            items = [i for i in items if not i.name.startswith(".")]
        
        # 排序：目录在前，文件在后
        dirs = sorted([i for i in items if i.is_dir()])
        files = sorted([i for i in items if i.is_file()])
        
        result = f"📁 目录: {dir_path.absolute()}\n\n"
        
        if dirs:
            result += "📂 子目录:\n"
            for d in dirs[:50]:
                result += f"  {d.relative_to(dir_path) if recursive else d.name}/\n"
            if len(dirs) > 50:
                result += f"  ... 还有 {len(dirs) - 50} 个目录\n"
        
        if files:
            result += "\n📄 文件:\n"
            for f in files[:100]:
                size = f.stat().st_size
                size_str = f"{size:,}" if size < 1024 else f"{size/1024:.1f}K"
                name = f.relative_to(dir_path) if recursive else f.name
                result += f"  {name} ({size_str})\n"
            if len(files) > 100:
                result += f"  ... 还有 {len(files) - 100} 个文件\n"
        
        result += f"\n统计: {len(dirs)} 个目录, {len(files)} 个文件"
        
        return result
        
    except PermissionError:
        return f"❌ 权限不足: {path}"
    except Exception as e:
        return f"❌ 列出目录失败: {str(e)}"


# ==================== 时间工具 ====================

@tool
def get_current_time() -> str:
    """
    获取当前日期和时间。
    
    用于回答关于当前时间、日期的问题。
    
    Returns:
        当前日期时间的格式化字符串
    
    Examples:
        >>> get_current_time()
        "2024-01-15 14:30:25 (星期一)"
    """
    now = datetime.now()
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekdays[now.weekday()]
    return f"{now.strftime('%Y-%m-%d %H:%M:%S')} ({weekday})"


# ==================== 工具集合 ====================

def get_practical_tools() -> List:
    """
    获取实用工具集
    
    Returns:
        实用工具列表
    """
    return [
        get_current_time,
        shell_execute,
        file_write,
        file_read_enhanced,
        web_fetch,
        process_list,
        env_info,
        list_directory,
    ]


# ==================== 导出 ====================

__all__ = [
    "get_current_time",
    "shell_execute",
    "file_write",
    "file_read_enhanced",
    "web_fetch",
    "process_list",
    "env_info",
    "list_directory",
    "get_practical_tools",
]


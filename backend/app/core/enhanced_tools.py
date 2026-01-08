# -*- coding: utf-8 -*-
"""
增强工具集 - Enhanced Tools

参考 OpenCode 的工具实现：
1. 语义代码搜索 (codesearch) - 使用 embedding 进行语义搜索
2. 多文件编辑 (multiedit) - 批量编辑多个文件
3. 批量操作 (batch) - 并行执行多个工具调用
4. Grep 增强 - 支持正则和上下文
5. Glob 文件匹配 - 高效文件查找
"""
import os
import re
import asyncio
import fnmatch
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from langchain.tools import tool
from loguru import logger
import json

from ..config import settings


# ==================== 1. 语义代码搜索 ====================

@dataclass
class CodeSearchResult:
    """代码搜索结果"""
    file_path: str
    content: str
    line_start: int
    line_end: int
    score: float
    context: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "score": self.score,
            "content": self.content,
            "context": self.context,
        }


class SemanticCodeSearch:
    """
    语义代码搜索器
    
    使用 embedding 进行语义搜索，找到与查询语义相关的代码
    """
    
    def __init__(self, workspace_path: Optional[str] = None):
        self.workspace_path = workspace_path or os.getcwd()
        self._embedding_client = None
        self._index: Dict[str, List[Dict]] = {}  # 文件 -> chunks
    
    async def _get_embedding(self, text: str) -> List[float]:
        """获取文本的 embedding"""
        try:
            from ..rag.embeddings import embedding_generator
            return await embedding_generator.embed_text(text)
        except Exception as e:
            logger.warning(f"Embedding failed, using fallback: {e}")
            # 降级：使用简单的词袋模型
            return self._simple_embedding(text)
    
    def _simple_embedding(self, text: str) -> List[float]:
        """简单的词袋 embedding（降级方案）"""
        import hashlib
        # 使用 hash 生成伪 embedding
        words = text.lower().split()
        vec = [0.0] * 128
        for word in words:
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            for i in range(128):
                vec[i] += ((h >> i) & 1) * 0.1
        # 归一化
        norm = sum(v * v for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if len(vec1) != len(vec2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)
    
    async def search(
        self,
        query: str,
        file_patterns: Optional[List[str]] = None,
        top_k: int = 10,
        min_score: float = 0.3,
    ) -> List[CodeSearchResult]:
        """
        语义搜索代码
        
        Args:
            query: 搜索查询
            file_patterns: 文件模式列表（如 ["*.py", "*.js"]）
            top_k: 返回数量
            min_score: 最小相似度
        
        Returns:
            搜索结果列表
        """
        logger.info(f"Semantic code search: {query[:50]}...")
        
        # 获取查询 embedding
        query_embedding = await self._get_embedding(query)
        
        # 收集文件
        files = self._collect_files(file_patterns)
        
        results = []
        
        for file_path in files[:100]:  # 限制文件数量
            try:
                chunks = await self._get_file_chunks(file_path)
                
                for chunk in chunks:
                    chunk_embedding = await self._get_embedding(chunk["content"])
                    score = self._cosine_similarity(query_embedding, chunk_embedding)
                    
                    if score >= min_score:
                        results.append(CodeSearchResult(
                            file_path=file_path,
                            content=chunk["content"],
                            line_start=chunk["line_start"],
                            line_end=chunk["line_end"],
                            score=score,
                            context=chunk.get("context", ""),
                        ))
            except Exception as e:
                logger.debug(f"Error processing {file_path}: {e}")
                continue
        
        # 按相似度排序
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results[:top_k]
    
    def _collect_files(
        self,
        patterns: Optional[List[str]] = None,
    ) -> List[str]:
        """收集文件"""
        if patterns is None:
            patterns = ["*.py", "*.js", "*.ts", "*.java", "*.go", "*.rs", "*.cpp", "*.c", "*.h"]
        
        files = []
        workspace = Path(self.workspace_path)
        
        # 排除模式
        exclude_dirs = {".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build"}
        
        for pattern in patterns:
            for file_path in workspace.rglob(pattern):
                # 检查排除目录
                if any(exc in file_path.parts for exc in exclude_dirs):
                    continue
                if file_path.is_file():
                    files.append(str(file_path))
        
        return files
    
    async def _get_file_chunks(
        self,
        file_path: str,
        chunk_size: int = 20,
        overlap: int = 5,
    ) -> List[Dict]:
        """
        将文件分块
        
        Args:
            file_path: 文件路径
            chunk_size: 每块行数
            overlap: 重叠行数
        
        Returns:
            块列表
        """
        chunks = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
        except Exception:
            return []
        
        for i in range(0, len(lines), chunk_size - overlap):
            chunk_lines = lines[i:i + chunk_size]
            if not chunk_lines:
                continue
            
            content = "".join(chunk_lines)
            
            # 获取上下文（函数/类名）
            context = self._extract_context(lines, i)
            
            chunks.append({
                "content": content,
                "line_start": i + 1,
                "line_end": i + len(chunk_lines),
                "context": context,
            })
        
        return chunks
    
    def _extract_context(self, lines: List[str], start_line: int) -> str:
        """提取上下文（函数/类定义）"""
        context_patterns = [
            r"^\s*(def|class|function|async function)\s+(\w+)",
            r"^\s*(public|private|protected)?\s*(static)?\s*(void|int|string|async)?\s+(\w+)\s*\(",
        ]
        
        # 向上查找最近的定义
        for i in range(start_line, max(0, start_line - 50), -1):
            if i >= len(lines):
                continue
            line = lines[i]
            for pattern in context_patterns:
                match = re.search(pattern, line)
                if match:
                    return line.strip()
        
        return ""


# ==================== 2. 多文件编辑 ====================

@dataclass
class FileEdit:
    """单个文件编辑"""
    file_path: str
    old_content: str
    new_content: str
    description: str = ""


@dataclass
class MultiEditResult:
    """多文件编辑结果"""
    success: List[str] = field(default_factory=list)
    failed: List[Dict[str, str]] = field(default_factory=list)
    
    @property
    def total(self) -> int:
        return len(self.success) + len(self.failed)
    
    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return len(self.success) / self.total


class MultiFileEditor:
    """
    多文件编辑器
    
    支持批量编辑多个文件
    """
    
    def __init__(self, workspace_path: Optional[str] = None):
        self.workspace_path = workspace_path or os.getcwd()
        self._backup_dir = os.path.join(self.workspace_path, ".agentic_chatbot", "backups")
    
    async def edit_files(
        self,
        edits: List[FileEdit],
        create_backup: bool = True,
        dry_run: bool = False,
    ) -> MultiEditResult:
        """
        批量编辑文件
        
        Args:
            edits: 编辑列表
            create_backup: 是否创建备份
            dry_run: 是否模拟运行
        
        Returns:
            编辑结果
        """
        result = MultiEditResult()
        
        for edit in edits:
            try:
                success = await self._apply_edit(
                    edit,
                    create_backup=create_backup,
                    dry_run=dry_run,
                )
                
                if success:
                    result.success.append(edit.file_path)
                else:
                    result.failed.append({
                        "file": edit.file_path,
                        "error": "Edit not applied (content not found)",
                    })
                    
            except Exception as e:
                result.failed.append({
                    "file": edit.file_path,
                    "error": str(e),
                })
        
        return result
    
    async def _apply_edit(
        self,
        edit: FileEdit,
        create_backup: bool = True,
        dry_run: bool = False,
    ) -> bool:
        """应用单个编辑"""
        file_path = Path(edit.file_path)
        
        if not file_path.is_absolute():
            file_path = Path(self.workspace_path) / file_path
        
        # 读取文件
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查旧内容是否存在
        if edit.old_content not in content:
            return False
        
        # 替换内容
        new_content = content.replace(edit.old_content, edit.new_content, 1)
        
        if dry_run:
            logger.info(f"[DRY RUN] Would edit: {file_path}")
            return True
        
        # 创建备份
        if create_backup:
            await self._create_backup(file_path, content)
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info(f"Edited: {file_path}")
        return True
    
    async def _create_backup(self, file_path: Path, content: str) -> str:
        """创建备份"""
        os.makedirs(self._backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}.{timestamp}.bak"
        backup_path = os.path.join(self._backup_dir, backup_name)
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return backup_path
    
    async def search_and_replace(
        self,
        pattern: str,
        replacement: str,
        file_patterns: Optional[List[str]] = None,
        is_regex: bool = False,
        dry_run: bool = False,
    ) -> MultiEditResult:
        """
        搜索并替换
        
        Args:
            pattern: 搜索模式
            replacement: 替换内容
            file_patterns: 文件模式
            is_regex: 是否使用正则
            dry_run: 是否模拟
        
        Returns:
            编辑结果
        """
        if file_patterns is None:
            file_patterns = ["*.py", "*.js", "*.ts", "*.json", "*.md"]
        
        workspace = Path(self.workspace_path)
        result = MultiEditResult()
        
        for file_pattern in file_patterns:
            for file_path in workspace.rglob(file_pattern):
                if not file_path.is_file():
                    continue
                
                # 排除目录
                if any(exc in str(file_path) for exc in [".git", "node_modules", "__pycache__"]):
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if is_regex:
                        new_content = re.sub(pattern, replacement, content)
                    else:
                        new_content = content.replace(pattern, replacement)
                    
                    if new_content != content:
                        if not dry_run:
                            await self._create_backup(file_path, content)
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                        
                        result.success.append(str(file_path))
                        
                except Exception as e:
                    result.failed.append({
                        "file": str(file_path),
                        "error": str(e),
                    })
        
        return result


# ==================== 3. 批量操作执行器 ====================

@dataclass
class BatchOperation:
    """批量操作"""
    tool_name: str
    args: Dict[str, Any]
    id: str = ""


@dataclass
class BatchResult:
    """批量操作结果"""
    results: List[Dict[str, Any]] = field(default_factory=list)
    total: int = 0
    success_count: int = 0
    failed_count: int = 0
    duration_ms: int = 0


class BatchExecutor:
    """
    批量操作执行器
    
    并行执行多个工具调用
    """
    
    def __init__(self, tool_registry: Optional[Dict[str, Callable]] = None):
        self.tools = tool_registry or {}
    
    def register_tool(self, name: str, func: Callable):
        """注册工具"""
        self.tools[name] = func
    
    async def execute(
        self,
        operations: List[BatchOperation],
        max_concurrent: int = 5,
    ) -> BatchResult:
        """
        批量执行操作
        
        Args:
            operations: 操作列表
            max_concurrent: 最大并发数
        
        Returns:
            执行结果
        """
        start_time = datetime.now()
        result = BatchResult(total=len(operations))
        
        # 使用 semaphore 限制并发
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_operation(op: BatchOperation) -> Dict[str, Any]:
            async with semaphore:
                try:
                    if op.tool_name not in self.tools:
                        return {
                            "id": op.id,
                            "success": False,
                            "error": f"Unknown tool: {op.tool_name}",
                        }
                    
                    tool_func = self.tools[op.tool_name]
                    
                    # 调用工具
                    if asyncio.iscoroutinefunction(tool_func):
                        output = await tool_func(**op.args)
                    else:
                        output = tool_func(**op.args)
                    
                    return {
                        "id": op.id,
                        "success": True,
                        "output": output,
                    }
                    
                except Exception as e:
                    return {
                        "id": op.id,
                        "success": False,
                        "error": str(e),
                    }
        
        # 并行执行
        tasks = [run_operation(op) for op in operations]
        results = await asyncio.gather(*tasks)
        
        result.results = results
        result.success_count = sum(1 for r in results if r.get("success"))
        result.failed_count = sum(1 for r in results if not r.get("success"))
        result.duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return result


# ==================== 4. Grep 增强 ====================

@tool
def grep_enhanced(
    pattern: str,
    path: str = ".",
    file_pattern: str = "*",
    context_lines: int = 2,
    is_regex: bool = True,
    case_sensitive: bool = True,
    max_results: int = 50,
) -> str:
    """
    增强版 Grep - 在文件中搜索模式。
    
    支持正则表达式、上下文显示、文件过滤。
    
    Args:
        pattern: 搜索模式（字符串或正则表达式）
        path: 搜索路径，默认当前目录
        file_pattern: 文件名模式（如 "*.py"）
        context_lines: 显示匹配行前后的行数
        is_regex: 是否使用正则表达式
        case_sensitive: 是否区分大小写
        max_results: 最大结果数
    
    Returns:
        搜索结果
    
    Examples:
        >>> grep_enhanced("def main", path="src", file_pattern="*.py")
        >>> grep_enhanced("TODO|FIXME", is_regex=True)
    """
    try:
        search_path = Path(path)
        if not search_path.exists():
            return f"❌ 路径不存在: {path}"
        
        # 编译正则
        flags = 0 if case_sensitive else re.IGNORECASE
        if is_regex:
            regex = re.compile(pattern, flags)
        else:
            regex = re.compile(re.escape(pattern), flags)
        
        results = []
        files_searched = 0
        matches_found = 0
        
        # 收集文件
        if search_path.is_file():
            files = [search_path]
        else:
            files = list(search_path.rglob(file_pattern))
        
        # 排除目录
        exclude_dirs = {".git", "node_modules", "__pycache__", "venv", ".venv"}
        
        for file_path in files:
            if not file_path.is_file():
                continue
            if any(exc in str(file_path) for exc in exclude_dirs):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                
                files_searched += 1
                
                for i, line in enumerate(lines):
                    if regex.search(line):
                        matches_found += 1
                        
                        if matches_found > max_results:
                            break
                        
                        # 获取上下文
                        start = max(0, i - context_lines)
                        end = min(len(lines), i + context_lines + 1)
                        context = lines[start:end]
                        
                        # 格式化输出
                        result_lines = []
                        for j, ctx_line in enumerate(context, start=start + 1):
                            prefix = ">" if j == i + 1 else " "
                            result_lines.append(f"{prefix} {j:4d} | {ctx_line.rstrip()}")
                        
                        results.append({
                            "file": str(file_path),
                            "line": i + 1,
                            "context": "\n".join(result_lines),
                        })
                
                if matches_found > max_results:
                    break
                    
            except Exception:
                continue
        
        if not results:
            return f"🔍 未找到匹配: '{pattern}'\n搜索了 {files_searched} 个文件"
        
        # 格式化输出
        output_parts = [f"🔍 搜索结果: '{pattern}'\n"]
        output_parts.append(f"找到 {len(results)} 个匹配（共搜索 {files_searched} 个文件）\n")
        
        for result in results:
            output_parts.append(f"\n📄 {result['file']}:{result['line']}")
            output_parts.append(f"```\n{result['context']}\n```")
        
        if matches_found > max_results:
            output_parts.append(f"\n⚠️ 结果已截断，共有超过 {max_results} 个匹配")
        
        return "\n".join(output_parts)
        
    except re.error as e:
        return f"❌ 正则表达式错误: {e}"
    except Exception as e:
        return f"❌ 搜索失败: {e}"


# ==================== 5. Glob 文件匹配 ====================

@tool
def glob_search(
    pattern: str,
    path: str = ".",
    max_results: int = 100,
    include_size: bool = True,
    sort_by: str = "name",
) -> str:
    """
    Glob 文件搜索 - 使用模式匹配查找文件。
    
    Args:
        pattern: Glob 模式（如 "**/*.py", "src/**/*.ts"）
        path: 搜索起始路径
        max_results: 最大结果数
        include_size: 是否显示文件大小
        sort_by: 排序方式 - "name", "size", "mtime"
    
    Returns:
        匹配的文件列表
    
    Examples:
        >>> glob_search("**/*.py")
        >>> glob_search("src/**/*.ts", sort_by="mtime")
    """
    try:
        search_path = Path(path)
        if not search_path.exists():
            return f"❌ 路径不存在: {path}"
        
        # 执行 glob
        matches = list(search_path.glob(pattern))
        
        # 过滤文件
        files = [m for m in matches if m.is_file()]
        
        # 排除目录
        exclude_dirs = {".git", "node_modules", "__pycache__", "venv", ".venv"}
        files = [f for f in files if not any(exc in str(f) for exc in exclude_dirs)]
        
        # 排序
        if sort_by == "size":
            files.sort(key=lambda f: f.stat().st_size, reverse=True)
        elif sort_by == "mtime":
            files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        else:
            files.sort(key=lambda f: str(f))
        
        # 截断
        truncated = len(files) > max_results
        files = files[:max_results]
        
        if not files:
            return f"🔍 未找到匹配: '{pattern}'"
        
        # 格式化输出
        output_parts = [f"🔍 Glob 搜索: '{pattern}'"]
        output_parts.append(f"找到 {len(files)} 个文件" + (" (已截断)" if truncated else ""))
        output_parts.append("")
        
        for f in files:
            rel_path = f.relative_to(search_path) if f.is_relative_to(search_path) else f
            
            if include_size:
                size = f.stat().st_size
                if size < 1024:
                    size_str = f"{size}B"
                elif size < 1024 * 1024:
                    size_str = f"{size/1024:.1f}KB"
                else:
                    size_str = f"{size/1024/1024:.1f}MB"
                output_parts.append(f"  {rel_path} ({size_str})")
            else:
                output_parts.append(f"  {rel_path}")
        
        return "\n".join(output_parts)
        
    except Exception as e:
        return f"❌ Glob 搜索失败: {e}"


# ==================== 工具函数封装 ====================

@tool
async def semantic_code_search(
    query: str,
    file_types: str = "py,js,ts",
    top_k: int = 5,
) -> str:
    """
    语义代码搜索 - 使用自然语言查找相关代码。
    
    这个工具使用语义理解来查找与你的描述相关的代码，
    不需要知道确切的函数名或关键字。
    
    Args:
        query: 自然语言查询（如 "处理用户认证的代码", "数据库连接逻辑"）
        file_types: 文件类型，逗号分隔（如 "py,js,ts"）
        top_k: 返回结果数量
    
    Returns:
        相关代码片段
    
    Examples:
        >>> semantic_code_search("用户登录验证")
        >>> semantic_code_search("API 请求处理", file_types="py")
    """
    try:
        searcher = SemanticCodeSearch()
        
        # 解析文件类型
        patterns = [f"*.{ext.strip()}" for ext in file_types.split(",")]
        
        results = await searcher.search(query, file_patterns=patterns, top_k=top_k)
        
        if not results:
            return f"🔍 未找到与 '{query}' 相关的代码"
        
        output_parts = [f"🔍 语义搜索: '{query}'", f"找到 {len(results)} 个相关代码片段", ""]
        
        for i, result in enumerate(results, 1):
            output_parts.append(f"### {i}. {result.file_path}")
            output_parts.append(f"行 {result.line_start}-{result.line_end} (相似度: {result.score:.2f})")
            if result.context:
                output_parts.append(f"上下文: {result.context}")
            output_parts.append(f"```\n{result.content}\n```")
            output_parts.append("")
        
        return "\n".join(output_parts)
        
    except Exception as e:
        return f"❌ 语义搜索失败: {e}"


@tool
async def multi_file_edit(
    edits_json: str,
    dry_run: bool = False,
) -> str:
    """
    多文件编辑 - 批量编辑多个文件。
    
    Args:
        edits_json: 编辑列表的 JSON 字符串，格式:
            [
                {"file": "path/to/file.py", "old": "旧内容", "new": "新内容"},
                ...
            ]
        dry_run: 是否模拟运行（不实际修改文件）
    
    Returns:
        编辑结果
    
    Examples:
        >>> multi_file_edit('[{"file": "a.py", "old": "foo", "new": "bar"}]')
    """
    try:
        edits_data = json.loads(edits_json)
        
        edits = [
            FileEdit(
                file_path=e["file"],
                old_content=e["old"],
                new_content=e["new"],
                description=e.get("desc", ""),
            )
            for e in edits_data
        ]
        
        editor = MultiFileEditor()
        result = await editor.edit_files(edits, dry_run=dry_run)
        
        output_parts = ["📝 多文件编辑结果"]
        output_parts.append(f"成功: {len(result.success)}, 失败: {len(result.failed)}")
        
        if result.success:
            output_parts.append("\n✅ 成功编辑:")
            for f in result.success:
                output_parts.append(f"  - {f}")
        
        if result.failed:
            output_parts.append("\n❌ 编辑失败:")
            for f in result.failed:
                output_parts.append(f"  - {f['file']}: {f['error']}")
        
        if dry_run:
            output_parts.append("\n⚠️ 这是模拟运行，未实际修改文件")
        
        return "\n".join(output_parts)
        
    except json.JSONDecodeError as e:
        return f"❌ JSON 解析错误: {e}"
    except Exception as e:
        return f"❌ 多文件编辑失败: {e}"


@tool
def search_and_replace_all(
    search: str,
    replace: str,
    file_pattern: str = "*.py",
    path: str = ".",
    is_regex: bool = False,
    dry_run: bool = True,
) -> str:
    """
    全局搜索替换 - 在多个文件中搜索并替换。
    
    ⚠️ 默认为模拟运行，需要设置 dry_run=False 才会实际修改。
    
    Args:
        search: 搜索内容
        replace: 替换内容
        file_pattern: 文件模式（如 "*.py"）
        path: 搜索路径
        is_regex: 是否使用正则表达式
        dry_run: 是否模拟运行
    
    Returns:
        替换结果
    
    Examples:
        >>> search_and_replace_all("old_name", "new_name", file_pattern="*.py")
    """
    try:
        import asyncio
        
        editor = MultiFileEditor(workspace_path=path)
        
        # 使用 asyncio.run 执行异步函数
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                editor.search_and_replace(
                    pattern=search,
                    replacement=replace,
                    file_patterns=[file_pattern],
                    is_regex=is_regex,
                    dry_run=dry_run,
                )
            )
        finally:
            loop.close()
        
        output_parts = ["🔄 搜索替换结果"]
        output_parts.append(f"搜索: '{search}' -> 替换: '{replace}'")
        output_parts.append(f"修改文件数: {len(result.success)}")
        
        if result.success:
            output_parts.append("\n修改的文件:")
            for f in result.success[:20]:
                output_parts.append(f"  - {f}")
            if len(result.success) > 20:
                output_parts.append(f"  ... 还有 {len(result.success) - 20} 个文件")
        
        if result.failed:
            output_parts.append("\n失败:")
            for f in result.failed[:5]:
                output_parts.append(f"  - {f['file']}: {f['error']}")
        
        if dry_run:
            output_parts.append("\n⚠️ 模拟运行 - 设置 dry_run=False 以实际修改")
        
        return "\n".join(output_parts)
        
    except Exception as e:
        return f"❌ 搜索替换失败: {e}"


# ==================== 工具集合 ====================

def get_enhanced_tools() -> List:
    """获取增强工具集"""
    return [
        grep_enhanced,
        glob_search,
        semantic_code_search,
        multi_file_edit,
        search_and_replace_all,
    ]


__all__ = [
    "SemanticCodeSearch",
    "CodeSearchResult",
    "MultiFileEditor",
    "FileEdit",
    "MultiEditResult",
    "BatchExecutor",
    "BatchOperation",
    "BatchResult",
    "grep_enhanced",
    "glob_search",
    "semantic_code_search",
    "multi_file_edit",
    "search_and_replace_all",
    "get_enhanced_tools",
]



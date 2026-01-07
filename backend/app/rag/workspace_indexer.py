# -*- coding: utf-8 -*-
"""
Workspace 自动索引器 - Workspace Indexer

自动扫描并索引工作区文件，让 AI 自动了解项目内容。

特性:
1. 智能文件过滤 (gitignore, 二进制文件等)
2. 优先级索引 (README, docs 优先)
3. 增量更新 (只索引变化的文件)
4. 后台索引 (不阻塞主流程)
"""
import os
import asyncio
import hashlib
import json
import fnmatch
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

from .vector_store import vector_store
from .document_processor import DocumentProcessor
from ..models.document import DocumentChunk
from ..config import settings


@dataclass
class FileInfo:
    """文件信息"""
    path: str
    relative_path: str
    size: int
    modified_time: float
    content_hash: Optional[str] = None
    priority: int = 5  # 1-10, 1最高


@dataclass
class IndexingStatus:
    """索引状态"""
    total_files: int = 0
    indexed_files: int = 0
    skipped_files: int = 0
    failed_files: int = 0
    is_complete: bool = False
    current_file: Optional[str] = None
    errors: List[str] = field(default_factory=list)


class WorkspaceIndexer:
    """
    工作区自动索引器
    
    使用示例:
    ```python
    indexer = WorkspaceIndexer("/path/to/project")
    
    # 同步快速扫描
    files = indexer.scan_files()
    
    # 异步索引
    await indexer.index_workspace()
    
    # 检查状态
    status = indexer.get_status()
    ```
    """
    
    # 默认忽略模式
    DEFAULT_IGNORE_PATTERNS = [
        # 版本控制
        '.git/', '.svn/', '.hg/',
        # 依赖目录
        'node_modules/', 'venv/', '.venv/', 'env/',
        '__pycache__/', '.pytest_cache/', '.mypy_cache/',
        # 构建输出
        'build/', 'dist/', '*.egg-info/',
        'target/', 'out/', 'bin/', 'obj/',
        # IDE 配置
        '.idea/', '.vscode/', '.cursor/',
        # 临时文件
        '*.pyc', '*.pyo', '*.pyd',
        '*.so', '*.dll', '*.dylib',
        '*.log', '*.tmp', '*.temp',
        '*.swp', '*.swo', '*~',
        # 二进制/媒体文件
        '*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.ico',
        '*.mp3', '*.mp4', '*.avi', '*.mov', '*.wav',
        '*.zip', '*.tar', '*.gz', '*.rar', '*.7z',
        '*.pdf', '*.doc', '*.docx', '*.xls', '*.xlsx',
        '*.exe', '*.bin', '*.dat',
        # 数据库
        '*.db', '*.sqlite', '*.sqlite3',
        # 锁文件
        'package-lock.json', 'yarn.lock', 'poetry.lock',
        'Pipfile.lock', 'pnpm-lock.yaml',
        # 其他
        '.DS_Store', 'Thumbs.db',
        '.env', '.env.*', '*.env',
        'data/', 'logs/', 'htmlcov/',
    ]
    
    # 高优先级文件模式 (优先索引)
    HIGH_PRIORITY_PATTERNS = [
        'README*', 'readme*',
        'ARCHITECTURE*', 'DESIGN*',
        'CONTRIBUTING*', 'CHANGELOG*',
        'docs/*.md', 'doc/*.md',
        '*.md',  # 所有 Markdown 文件
    ]
    
    # 中优先级文件模式
    MEDIUM_PRIORITY_PATTERNS = [
        'src/*.py', 'app/*.py', 'lib/*.py',
        'src/*.ts', 'src/*.js',
        'main.py', 'app.py', 'index.py',
        'main.ts', 'index.ts', 'app.ts',
        '*.yaml', '*.yml', '*.toml',
        'config/*', 'configs/*',
    ]
    
    # 支持的文本文件扩展名
    TEXT_EXTENSIONS = {
        # 代码
        '.py', '.js', '.ts', '.jsx', '.tsx',
        '.java', '.c', '.cpp', '.h', '.hpp',
        '.go', '.rs', '.rb', '.php', '.swift',
        '.kt', '.scala', '.cs', '.vb',
        '.sh', '.bash', '.zsh', '.fish',
        '.ps1', '.bat', '.cmd',
        # 标记语言
        '.md', '.markdown', '.rst', '.txt',
        '.html', '.htm', '.xml', '.svg',
        # 配置
        '.json', '.yaml', '.yml', '.toml',
        '.ini', '.cfg', '.conf',
        '.env.example', '.editorconfig',
        # 其他
        '.css', '.scss', '.sass', '.less',
        '.sql', '.graphql', '.proto',
        'Dockerfile', 'Makefile', 'Jenkinsfile',
        '.gitignore', '.dockerignore',
    }
    
    def __init__(
        self,
        workspace_path: str,
        custom_ignore_patterns: Optional[List[str]] = None,
        max_file_size_kb: int = 500,
        index_cache_path: Optional[str] = None,
    ):
        """
        初始化工作区索引器
        
        Args:
            workspace_path: 工作区根目录
            custom_ignore_patterns: 自定义忽略模式
            max_file_size_kb: 单文件大小限制 (KB)
            index_cache_path: 索引缓存路径
        """
        self.workspace_path = Path(workspace_path).resolve()
        self.max_file_size = max_file_size_kb * 1024  # 转为字节
        
        # 合并忽略模式
        self.ignore_patterns = set(self.DEFAULT_IGNORE_PATTERNS)
        if custom_ignore_patterns:
            self.ignore_patterns.update(custom_ignore_patterns)
        
        # 加载 .gitignore
        self._load_gitignore()
        
        # 索引缓存
        self.index_cache_path = Path(index_cache_path) if index_cache_path else (
            self.workspace_path / '.cache' / 'workspace_index.json'
        )
        self.file_hashes: Dict[str, str] = {}
        self._load_index_cache()
        
        # 状态
        self.status = IndexingStatus()
        self._is_indexing = False
        
        # 文档处理器
        self.doc_processor = DocumentProcessor()
        
        logger.info(f"WorkspaceIndexer initialized for: {self.workspace_path}")
    
    def _load_gitignore(self):
        """加载 .gitignore 规则"""
        gitignore_path = self.workspace_path / '.gitignore'
        if gitignore_path.exists():
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self.ignore_patterns.add(line)
                logger.debug(f"Loaded .gitignore patterns")
            except Exception as e:
                logger.warning(f"Failed to load .gitignore: {e}")
    
    def _load_index_cache(self):
        """加载索引缓存"""
        if self.index_cache_path.exists():
            try:
                with open(self.index_cache_path, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    self.file_hashes = cache.get('file_hashes', {})
                logger.debug(f"Loaded index cache with {len(self.file_hashes)} entries")
            except Exception as e:
                logger.warning(f"Failed to load index cache: {e}")
    
    def _save_index_cache(self):
        """保存索引缓存"""
        try:
            self.index_cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.index_cache_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'file_hashes': self.file_hashes,
                    'last_updated': datetime.now().isoformat(),
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save index cache: {e}")
    
    def _should_ignore(self, path: Path) -> bool:
        """检查文件是否应该被忽略"""
        rel_path = str(path.relative_to(self.workspace_path))
        
        for pattern in self.ignore_patterns:
            # 目录模式
            if pattern.endswith('/'):
                dir_pattern = pattern.rstrip('/')
                if any(part == dir_pattern for part in path.parts):
                    return True
            # 文件模式
            elif fnmatch.fnmatch(path.name, pattern):
                return True
            elif fnmatch.fnmatch(rel_path, pattern):
                return True
        
        return False
    
    def _is_text_file(self, path: Path) -> bool:
        """检查是否是文本文件"""
        # 检查扩展名
        if path.suffix.lower() in self.TEXT_EXTENSIONS:
            return True
        
        # 检查无扩展名的特殊文件
        if path.name in ['Dockerfile', 'Makefile', 'Jenkinsfile', 'Vagrantfile']:
            return True
        
        # 检查文件名模式
        if path.name.startswith('.') and path.suffix == '':
            # .gitignore, .dockerignore 等
            return True
        
        return False
    
    def _get_priority(self, path: Path) -> int:
        """
        获取文件索引优先级
        
        Returns:
            1-10, 1 最高优先级
        """
        rel_path = str(path.relative_to(self.workspace_path))
        name = path.name
        
        # 高优先级
        for pattern in self.HIGH_PRIORITY_PATTERNS:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel_path, pattern):
                return 1
        
        # 中优先级
        for pattern in self.MEDIUM_PRIORITY_PATTERNS:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel_path, pattern):
                return 3
        
        # 测试文件较低优先级
        if 'test' in rel_path.lower() or 'spec' in rel_path.lower():
            return 7
        
        # 示例文件较低优先级
        if 'example' in rel_path.lower() or 'sample' in rel_path.lower():
            return 8
        
        # 默认优先级
        return 5
    
    def _compute_hash(self, path: Path) -> str:
        """计算文件内容哈希"""
        try:
            with open(path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def scan_files(self) -> List[FileInfo]:
        """
        扫描工作区文件
        
        Returns:
            文件信息列表，按优先级排序
        """
        files: List[FileInfo] = []
        
        for root, dirs, filenames in os.walk(self.workspace_path):
            root_path = Path(root)
            
            # 过滤目录
            dirs[:] = [d for d in dirs if not self._should_ignore(root_path / d)]
            
            for filename in filenames:
                file_path = root_path / filename
                
                # 检查是否应该忽略
                if self._should_ignore(file_path):
                    continue
                
                # 检查是否是文本文件
                if not self._is_text_file(file_path):
                    continue
                
                try:
                    stat = file_path.stat()
                    
                    # 检查文件大小
                    if stat.st_size > self.max_file_size:
                        logger.debug(f"Skipping large file: {file_path}")
                        continue
                    
                    # 跳过空文件
                    if stat.st_size == 0:
                        continue
                    
                    files.append(FileInfo(
                        path=str(file_path),
                        relative_path=str(file_path.relative_to(self.workspace_path)),
                        size=stat.st_size,
                        modified_time=stat.st_mtime,
                        priority=self._get_priority(file_path),
                    ))
                    
                except Exception as e:
                    logger.warning(f"Failed to stat file {file_path}: {e}")
        
        # 按优先级排序
        files.sort(key=lambda f: (f.priority, f.relative_path))
        
        logger.info(f"Scanned {len(files)} files in workspace")
        return files
    
    async def index_workspace(
        self,
        force: bool = False,
        priority_only: bool = False,
        progress_callback: Optional[callable] = None,
    ) -> IndexingStatus:
        """
        索引工作区
        
        Args:
            force: 强制重新索引所有文件
            priority_only: 只索引高优先级文件
            progress_callback: 进度回调函数
        
        Returns:
            索引状态
        """
        if self._is_indexing:
            logger.warning("Indexing already in progress")
            return self.status
        
        self._is_indexing = True
        self.status = IndexingStatus()
        
        try:
            # 扫描文件
            files = self.scan_files()
            
            # 过滤高优先级文件
            if priority_only:
                files = [f for f in files if f.priority <= 3]
            
            self.status.total_files = len(files)
            
            logger.info(f"Starting indexing of {len(files)} files")
            
            for i, file_info in enumerate(files):
                self.status.current_file = file_info.relative_path
                
                try:
                    # 计算文件哈希
                    content_hash = self._compute_hash(Path(file_info.path))
                    
                    # 检查是否需要重新索引
                    if not force and self.file_hashes.get(file_info.relative_path) == content_hash:
                        self.status.skipped_files += 1
                        continue
                    
                    # 读取文件内容
                    with open(file_info.path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # 创建文档块
                    chunks = self._create_chunks(file_info, content)
                    
                    # 添加到向量库
                    if chunks:
                        await vector_store.add_chunks(chunks)
                    
                    # 更新缓存
                    self.file_hashes[file_info.relative_path] = content_hash
                    self.status.indexed_files += 1
                    
                    # 进度回调
                    if progress_callback:
                        progress_callback(i + 1, len(files), file_info.relative_path)
                    
                except Exception as e:
                    self.status.failed_files += 1
                    self.status.errors.append(f"{file_info.relative_path}: {str(e)}")
                    logger.warning(f"Failed to index {file_info.relative_path}: {e}")
            
            self.status.is_complete = True
            self.status.current_file = None
            
            # 保存缓存
            self._save_index_cache()
            
            logger.info(
                f"Indexing complete: {self.status.indexed_files} indexed, "
                f"{self.status.skipped_files} skipped, {self.status.failed_files} failed"
            )
            
        finally:
            self._is_indexing = False
        
        return self.status
    
    def _create_chunks(self, file_info: FileInfo, content: str) -> List[DocumentChunk]:
        """
        创建文档块
        
        Args:
            file_info: 文件信息
            content: 文件内容
        
        Returns:
            文档块列表
        """
        chunks = []
        
        # 使用文档处理器分块
        try:
            text_chunks = self.doc_processor.split_text(content)
        except Exception:
            # 简单分块作为后备
            chunk_size = 1000
            text_chunks = [
                content[i:i+chunk_size] 
                for i in range(0, len(content), chunk_size)
            ]
        
        for i, chunk_text in enumerate(text_chunks):
            if not chunk_text.strip():
                continue
            
            chunk_id = f"{file_info.relative_path}:{i}"
            
            chunks.append(DocumentChunk(
                id=chunk_id,
                document_id=file_info.relative_path,
                content=chunk_text,
                chunk_index=i,
                metadata={
                    'file_path': file_info.relative_path,
                    'file_size': file_info.size,
                    'priority': file_info.priority,
                    'source': 'workspace_auto_index',
                }
            ))
        
        return chunks
    
    async def index_file(self, file_path: str) -> bool:
        """
        索引单个文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            是否成功
        """
        path = Path(file_path)
        if not path.is_absolute():
            path = self.workspace_path / path
        
        if not path.exists():
            logger.warning(f"File not found: {path}")
            return False
        
        try:
            file_info = FileInfo(
                path=str(path),
                relative_path=str(path.relative_to(self.workspace_path)),
                size=path.stat().st_size,
                modified_time=path.stat().st_mtime,
                priority=self._get_priority(path),
            )
            
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            chunks = self._create_chunks(file_info, content)
            
            if chunks:
                await vector_store.add_chunks(chunks)
            
            # 更新缓存
            content_hash = self._compute_hash(path)
            self.file_hashes[file_info.relative_path] = content_hash
            self._save_index_cache()
            
            logger.info(f"Indexed file: {file_info.relative_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index file {path}: {e}")
            return False
    
    def get_status(self) -> IndexingStatus:
        """获取索引状态"""
        return self.status
    
    def get_indexed_files(self) -> List[str]:
        """获取已索引的文件列表"""
        return list(self.file_hashes.keys())
    
    def clear_index(self):
        """清除索引缓存"""
        self.file_hashes = {}
        if self.index_cache_path.exists():
            self.index_cache_path.unlink()
        logger.info("Index cache cleared")


# 全局实例工厂
_workspace_indexer: Optional[WorkspaceIndexer] = None


def get_workspace_indexer(workspace_path: Optional[str] = None) -> WorkspaceIndexer:
    """
    获取工作区索引器实例
    
    Args:
        workspace_path: 工作区路径，如果不提供则使用配置
    
    Returns:
        WorkspaceIndexer 实例
    """
    global _workspace_indexer
    
    if _workspace_indexer is None:
        path = workspace_path or getattr(settings, 'WORKSPACE_ROOT', os.getcwd())
        _workspace_indexer = WorkspaceIndexer(path)
    
    return _workspace_indexer


async def auto_index_workspace(
    workspace_path: Optional[str] = None,
    priority_only: bool = True,
) -> IndexingStatus:
    """
    自动索引工作区的便捷函数
    
    Args:
        workspace_path: 工作区路径
        priority_only: 是否只索引高优先级文件
    
    Returns:
        索引状态
    """
    indexer = get_workspace_indexer(workspace_path)
    return await indexer.index_workspace(priority_only=priority_only)


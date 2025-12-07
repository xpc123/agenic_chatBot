"""
上下文加载器 - Context Loader
支持@路径引用，加载本地文件作为对话上下文
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import os
import mimetypes
from loguru import logger
import fnmatch

from ..config import settings


class ContextLoader:
    """
    上下文加载器
    
    职责:
    1. 解析@路径引用
    2. 加载文件内容
    3. 验证权限和安全性
    4. 格式化为上下文
    """
    
    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = Path(workspace_root or settings.WORKSPACE_ROOT or os.getcwd())
        self.max_file_size = settings.MAX_FILE_SIZE_FOR_CONTEXT
        self.allowed_patterns = settings.ALLOWED_PATH_PATTERNS
        
        logger.info(f"ContextLoader initialized with root: {self.workspace_root}")
    
    async def load_context_from_message(self, message: str) -> Dict[str, Any]:
        """
        从消息中提取@路径引用并加载内容
        
        Args:
            message: 用户消息
        
        Returns:
            包含原始消息和加载的上下文
        """
        references = self._extract_path_references(message)
        
        if not references:
            return {
                "message": message,
                "contexts": []
            }
        
        contexts = []
        for ref in references:
            try:
                context = await self._load_single_reference(ref)
                if context:
                    contexts.append(context)
            except Exception as e:
                logger.error(f"Failed to load reference {ref}: {e}")
                contexts.append({
                    "path": ref,
                    "error": str(e),
                    "loaded": False
                })
        
        return {
            "message": message,
            "contexts": contexts,
            "references_count": len(references)
        }
    
    def _extract_path_references(self, message: str) -> List[str]:
        """
        提取消息中的@路径引用
        
        支持格式:
        - @/path/to/file.py
        - @./relative/path/file.md
        - @path/to/directory/
        """
        import re
        
        # 匹配 @路径 模式
        pattern = r'@([\w\-./]+(?:\.\w+)?)'
        matches = re.findall(pattern, message)
        
        return list(set(matches))  # 去重
    
    async def _load_single_reference(self, ref_path: str) -> Optional[Dict[str, Any]]:
        """
        加载单个路径引用
        
        Args:
            ref_path: 引用路径
        
        Returns:
            上下文字典
        """
        # 解析路径
        if ref_path.startswith('/'):
            # 绝对路径 (相对于workspace_root)
            full_path = self.workspace_root / ref_path.lstrip('/')
        else:
            # 相对路径
            full_path = self.workspace_root / ref_path
        
        # 规范化路径
        full_path = full_path.resolve()
        
        # 安全检查: 确保路径在workspace内
        if not self._is_safe_path(full_path):
            logger.warning(f"Unsafe path access attempted: {full_path}")
            raise ValueError(f"Path {ref_path} is outside workspace")
        
        # 检查路径是否存在
        if not full_path.exists():
            raise FileNotFoundError(f"Path not found: {ref_path}")
        
        # 处理目录
        if full_path.is_dir():
            return await self._load_directory(full_path, ref_path)
        
        # 处理文件
        return await self._load_file(full_path, ref_path)
    
    def _is_safe_path(self, path: Path) -> bool:
        """检查路径是否安全（在workspace内）"""
        try:
            path.resolve().relative_to(self.workspace_root.resolve())
            return True
        except ValueError:
            return False
    
    async def _load_file(self, file_path: Path, ref_path: str) -> Dict[str, Any]:
        """
        加载单个文件
        
        Args:
            file_path: 完整文件路径
            ref_path: 引用路径
        
        Returns:
            文件上下文
        """
        # 检查文件大小
        file_size = file_path.stat().st_size
        if file_size > self.max_file_size:
            raise ValueError(
                f"File too large: {file_size} bytes (max: {self.max_file_size})"
            )
        
        # 检查文件类型
        if not self._is_allowed_file(file_path):
            raise ValueError(f"File type not allowed: {file_path.suffix}")
        
        # 读取内容
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # 尝试其他编码
            content = file_path.read_text(encoding='latin-1')
        
        return {
            "type": "file",
            "path": ref_path,
            "full_path": str(file_path),
            "name": file_path.name,
            "extension": file_path.suffix,
            "content": content,
            "size": file_size,
            "lines": len(content.splitlines()),
            "loaded": True
        }
    
    async def _load_directory(
        self,
        dir_path: Path,
        ref_path: str,
        max_files: int = 20
    ) -> Dict[str, Any]:
        """
        加载目录结构
        
        Args:
            dir_path: 目录路径
            ref_path: 引用路径
            max_files: 最大文件数
        
        Returns:
            目录上下文
        """
        files = []
        file_count = 0
        
        for item in dir_path.rglob('*'):
            if file_count >= max_files:
                break
            
            if item.is_file() and self._is_allowed_file(item):
                try:
                    # 只获取文件信息，不加载内容
                    files.append({
                        "name": item.name,
                        "path": str(item.relative_to(self.workspace_root)),
                        "size": item.stat().st_size,
                        "type": item.suffix
                    })
                    file_count += 1
                except Exception as e:
                    logger.debug(f"Skip file {item}: {e}")
        
        return {
            "type": "directory",
            "path": ref_path,
            "full_path": str(dir_path),
            "files": files,
            "file_count": len(files),
            "loaded": True
        }
    
    def _is_allowed_file(self, file_path: Path) -> bool:
        """检查文件是否允许加载"""
        file_str = str(file_path)
        
        for pattern in self.allowed_patterns:
            if fnmatch.fnmatch(file_str, pattern):
                return True
        
        return False
    
    async def format_context_for_llm(
        self,
        contexts: List[Dict[str, Any]]
    ) -> str:
        """
        将上下文格式化为LLM可读格式
        
        Args:
            contexts: 上下文列表
        
        Returns:
            格式化的文本
        """
        if not contexts:
            return ""
        
        parts = ["## 引用的上下文\n"]
        
        for ctx in contexts:
            if not ctx.get("loaded"):
                parts.append(f"### ❌ {ctx['path']} (加载失败: {ctx.get('error', 'Unknown')})\n")
                continue
            
            if ctx["type"] == "file":
                parts.append(f"### 📄 {ctx['path']}\n")
                parts.append(f"```{ctx['extension'].lstrip('.')}\n")
                parts.append(ctx["content"])
                parts.append("\n```\n")
            
            elif ctx["type"] == "directory":
                parts.append(f"### 📁 {ctx['path']} ({ctx['file_count']} files)\n")
                for f in ctx["files"][:10]:  # 最多显示10个
                    parts.append(f"- {f['name']} ({f['size']} bytes)\n")
        
        return "\n".join(parts)

"""File Tool - 文件读写操作"""
import os
from .base import BaseTool, ToolResult


class FileTool(BaseTool):
    """文件读写操作"""

    name = "file_read"
    description = (
        "文件读写操作。支持：读文件(read)、写文件(write)、创建目录(mkdir)。"
        "命令格式: read:/path/to/file | write:/path/to/file:content | mkdir:/path/to/dir"
    )

    def __init__(self, base_dir: str = "/workspace"):
        self.base_dir = base_dir

    async def execute(self, command: str, **kwargs) -> ToolResult:
        try:
            op, _, rest = command.partition(":")
            op = op.strip().lower()

            if op == "read":
                return await self._read(rest.strip())
            elif op == "write":
                path, _, content = rest.partition(":")
                return await self._write(path.strip(), content)
            elif op == "mkdir":
                return await self._mkdir(rest.strip())
            elif op == "list":
                return await self._list(rest.strip() or ".")
            else:
                return ToolResult(success=False, stderr=f"未知操作: {op}", exit_code=1)
        except Exception as e:
            return ToolResult(success=False, stderr=str(e), exit_code=1)

    async def _read(self, path: str) -> ToolResult:
        full_path = self._safe_path(path)
        if not os.path.exists(full_path):
            return ToolResult(success=False, stderr=f"文件不存在: {path}", exit_code=1)
        file_size = os.path.getsize(full_path)
        if file_size > 10 * 1024 * 1024:  # 10MB
            return ToolResult(success=False, stderr=f"文件过大: {file_size} bytes (最大 10MB)", exit_code=1)
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        return ToolResult(success=True, stdout=content)

    async def _write(self, path: str, content: str) -> ToolResult:
        full_path = self._safe_path(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return ToolResult(success=True, stdout=f"文件已写入: {full_path}")

    async def _mkdir(self, path: str) -> ToolResult:
        full_path = self._safe_path(path)
        os.makedirs(full_path, exist_ok=True)
        return ToolResult(success=True, stdout=f"目录已创建: {full_path}")

    async def _list(self, path: str) -> ToolResult:
        full_path = self._safe_path(path)
        if not os.path.exists(full_path):
            return ToolResult(success=False, stderr=f"路径不存在: {path}", exit_code=1)
        items = os.listdir(full_path)
        return ToolResult(success=True, stdout="\n".join(items))

    def _safe_path(self, path: str) -> str:
        """确保路径在 base_dir 范围内"""
        full = os.path.abspath(os.path.join(self.base_dir, path))
        if not full.startswith(os.path.abspath(self.base_dir)):
            raise ValueError(f"路径越界: {path}")
        return full

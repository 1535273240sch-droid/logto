"""File Service - 文件管理服务"""
from ..base import BaseService


class FileService(BaseService):
    name = "file"
    
    async def upload(self, filename: str, content: bytes) -> dict:
        """上传文件"""
        return {"filename": filename, "status": "delegated"}

"""Image Service - 图片服务"""
from ..base import BaseService


class ImageService(BaseService):
    name = "image"
    
    async def generate(self, prompt: str) -> dict:
        """生成图片"""
        return {"prompt": prompt, "status": "delegated"}

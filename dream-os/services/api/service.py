"""API Service - 统一 API 接口层"""
from ..base import BaseService


class ApiService(BaseService):
    name = "api"
    
    async def register_routes(self, app):
        """注册 API 路由"""
        pass

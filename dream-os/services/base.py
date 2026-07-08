"""Base Service - 服务基类"""
from typing import Any, Dict


class BaseService:
    name = "base"
    version = "1.0.0"

    async def initialize(self):
        return self

    async def health_check(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": "healthy",
            "version": self.version,
        }
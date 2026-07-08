"""Model Service - AI 模型管理服务"""
from ..base import BaseService


class ModelService(BaseService):
    name = "model"
    version = "1.0.0"

    async def initialize(self):
        try:
            from dream_os.backend.app.config import get_settings
            self._settings = get_settings()
            self._model_available = True
        except ImportError:
            self._model_available = False
        return self

    async def get_models(self):
        return [
            {"id": "agnes-2.0-flash", "name": "Agnes 2.0 Flash", "provider": "agnes"},
            {"id": "agnes-2.0-pro", "name": "Agnes 2.0 Pro", "provider": "agnes"},
            {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai"},
            {"id": "deepseek-chat", "name": "DeepSeek Chat", "provider": "deepseek"},
            {"id": "glm-4-plus", "name": "GLM-4 Plus", "provider": "zhipu"},
            {"id": "qwen-plus", "name": "通义千问 Plus", "provider": "qwen"},
        ]

    async def set_model(self, model_name):
        if self._model_available and hasattr(self, "_settings"):
            self._settings.openai_model = model_name
            return {"model": model_name, "status": "ok"}
        return {"model": model_name, "status": "degraded"}

    async def health_check(self):
        return {
            "name": self.name,
            "status": "healthy" if getattr(self, "_model_available", False) else "degraded",
            "version": self.version,
        }
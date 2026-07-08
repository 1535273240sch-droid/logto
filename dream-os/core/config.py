"""Config - Dream OS 系统配置管理

Core 层的配置管理，统一管理系统配置。
"""
import os
import json
from typing import Any, Optional
from pathlib import Path


class CoreConfig:
    """系统核心配置 - 单例"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = {}
            cls._instance._load_defaults()
        return cls._instance

    def _load_defaults(self):
        self._config = {
            "system": {
                "name": "Dream OS",
                "version": "1.0.0",
                "debug": os.getenv("DEBUG", "false").lower() == "true",
                "environment": os.getenv("ENVIRONMENT", "production"),
            },
            "core": {
                "guardian_enabled": True,
                "brain_enabled": True,
            },
            "paths": {
                "workspace": os.getenv("DREAM_WORKSPACE_ROOT", "/workspace"),
                "projects": os.getenv("DREAM_WORKSPACE_ROOT", "/workspace/projects"),
            },
        }

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        val = self._config
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
        return val if val is not None else default

    def set(self, key: str, value: Any):
        keys = key.split(".")
        target = self._config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value

    def all(self) -> dict:
        return dict(self._config)


core_config = CoreConfig()


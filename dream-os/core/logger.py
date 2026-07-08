"""Logger - Dream OS 统一日志系统

所有模块统一使用 Core Logger。
支持结构化日志、多级别、上下文追踪。
"""
import logging
import sys
from datetime import datetime


class CoreLogger:
    """系统日志核心"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_logger()
        return cls._instance

    def _init_logger(self):
        formatter = logging.Formatter(
            "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)

        self._logger = logging.getLogger("dream-os")
        self._logger.setLevel(logging.INFO)
        self._logger.handlers.clear()
        self._logger.addHandler(handler)
        self._logger.propagate = False

    def get_logger(self, name: str = None) -> logging.Logger:
        if name:
            return self._logger.getChild(name)
        return self._logger

    def info(self, msg: str, **kwargs):
        extra = f" | {kwargs}" if kwargs else ""
        self._logger.info(f"{msg}{extra}")

    def warning(self, msg: str, **kwargs):
        extra = f" | {kwargs}" if kwargs else ""
        self._logger.warning(f"{msg}{extra}")

    def error(self, msg: str, **kwargs):
        extra = f" | {kwargs}" if kwargs else ""
        self._logger.error(f"{msg}{extra}")

    def debug(self, msg: str, **kwargs):
        extra = f" | {kwargs}" if kwargs else ""
        self._logger.debug(f"{msg}{extra}")


core_logger = CoreLogger()


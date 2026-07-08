"""成果物生成器基类"""
import abc
from pathlib import Path
from typing import Optional


class BaseGenerator(abc.ABC):
    """生成器基类 — 所有成果物生成器必须继承"""

    @property
    @abc.abstractmethod
    def supported_types(self) -> list[str]:
        """支持的成果物类型列表"""
        pass

    @abc.abstractmethod
    async def generate(self, content: str, output_path: Path,
                       title: str = "", **kwargs) -> dict:
        """生成成果物"""
        pass

    def _ensure_dir(self, output_path: Path):
        """确保输出目录存在"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

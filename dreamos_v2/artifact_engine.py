"""Artifact Engine — 成果物引擎

核心模块：统一成果物生成、管理、存储
所有 AI 回复结束后，自动判断并生成最合适的成果物
"""
import os
import time
import json
import uuid
import logging
import asyncio
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Any
from datetime import datetime

logger = logging.getLogger("dream-os.artifact")

# ── 成果物存储目录 ──────────────────────────────
ARTIFACT_DIR = Path(os.getenv("ARTIFACT_DIR", "/workspace/artifacts"))
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Artifact:
    """单个成果物"""
    id: str = ""
    filename: str = ""
    artifact_type: str = ""
    category: str = ""
    title: str = ""
    description: str = ""
    filepath: str = ""
    file_size: int = 0
    content_preview: str = ""
    status: str = "pending"  # pending / generating / completed / failed
    created_at: str = ""
    conversation_id: str = ""
    project_id: str = ""
    generation_time_ms: int = 0
    error: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = uuid.uuid4().hex[:12]
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def icon(self) -> str:
        """成果物图标"""
        icons = {
            "markdown": "📝", "word": "📁", "pdf": "📄", "html": "🌐", "txt": "📃",
            "excel": "📊", "csv": "📊", "markdown_table": "📋",
            "ppt": "📽", "speech": "🎤",
            "mermaid": "🔀", "mindmap": "🧠", "flowchart": "🔄", "architecture": "🏗",
            "er_diagram": "🗃", "sequence_diagram": "↔", "gantt": "📅", "org_chart": "👥",
            "bar_chart": "📊", "line_chart": "📈", "pie_chart": "🥧",
            "radar_chart": "🎯", "trend_chart": "📉",
            "code": "💻", "api_doc": "📖",
        }
        return icons.get(self.artifact_type, "📦")

    @property
    def extension(self) -> str:
        """文件扩展名"""
        exts = {
            "markdown": ".md", "word": ".docx", "pdf": ".pdf", "html": ".html", "txt": ".txt",
            "excel": ".xlsx", "csv": ".csv", "markdown_table": ".md",
            "ppt": ".pptx", "speech": ".md",
            "mermaid": ".mmd", "mindmap": ".mmd", "flowchart": ".mmd", "architecture": ".mmd",
            "er_diagram": ".mmd", "sequence_diagram": ".mmd", "gantt": ".mmd", "org_chart": ".mmd",
            "bar_chart": ".svg", "line_chart": ".svg", "pie_chart": ".svg",
            "radar_chart": ".svg", "trend_chart": ".svg",
            "code": ".py", "api_doc": ".md",
        }
        return exts.get(self.artifact_type, ".bin")


class ArtifactEngine:
    """成果物引擎 — 统一生成、管理、存储

    工作流程：
    1. 接收用户输入 + AI 回答
    2. OutputRouter 决定生成什么成果物
    3. 调用对应的 Generator 生成
    4. 保存文件 + 记录元数据
    5. 返回成果物信息给前端
    """

    def __init__(self):
        self._generators = {}
        self._registry: dict[str, Artifact] = {}
        self._init_generators()

    def _init_generators(self):
        """初始化所有生成器"""
        from .generators.markdown_gen import MarkdownGenerator
        from .generators.chart_gen import ChartGenerator
        from .generators.mermaid_gen import MermaidGenerator
        from .generators.excel_gen import ExcelGenerator
        from .generators.pdf_gen import PdfGenerator
        from .generators.ppt_gen import PptGenerator
        from .generators.word_gen import WordGenerator

        generators = [
            MarkdownGenerator(), ChartGenerator(), MermaidGenerator(),
            ExcelGenerator(), PdfGenerator(), PptGenerator(), WordGenerator(),
        ]
        for gen in generators:
            for supported_type in gen.supported_types:
                self._generators[supported_type] = gen
            logger.info(f"Generator registered: {gen.__class__.__name__} "
                        f"→ {gen.supported_types}")

    def get_generator(self, artifact_type: str):
        return self._generators.get(artifact_type)

    def list_supported_types(self) -> list[str]:
        return list(self._generators.keys())

    async def generate(self, artifact_type: str, content: str,
                       title: str = "", conversation_id: str = "",
                       project_id: str = "", **kwargs) -> Artifact:
        """生成单个成果物

        Args:
            artifact_type: 成果物类型
            content: AI 回答内容
            title: 成果物标题
            conversation_id: 会话ID
            project_id: 项目ID

        Returns:
            Artifact 包含文件路径和元数据
        """
        artifact = Artifact(
            artifact_type=artifact_type,
            title=title or artifact_type,
            conversation_id=conversation_id,
            project_id=project_id,
            status="generating",
        )

        generator = self.get_generator(artifact_type)
        if not generator:
            artifact.status = "failed"
            artifact.error = f"不支持的成果物类型: {artifact_type}"
            logger.warning(f"No generator for type: {artifact_type}")
            return artifact

        start_time = time.time()
        try:
            # 生成文件
            filename = f"{artifact.id}_{title or artifact_type}{artifact.extension}"
            output_path = ARTIFACT_DIR / filename

            result = await generator.generate(content, output_path, title=title, **kwargs)

            # 更新成果物信息
            artifact.filename = filename
            artifact.filepath = str(output_path)
            artifact.file_size = output_path.stat().st_size if output_path.exists() else 0
            artifact.content_preview = content[:200] if content else ""
            artifact.status = "completed"
            artifact.generation_time_ms = int((time.time() - start_time) * 1000)

            logger.info(f"Artifact generated: {artifact_type} → {filename} "
                        f"({artifact.generation_time_ms}ms, {artifact.file_size} bytes)")

        except Exception as e:
            artifact.status = "failed"
            artifact.error = str(e)[:500]
            artifact.generation_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Artifact generation failed: {artifact_type} → {e}", exc_info=True)

        # 记录到注册表
        self._registry[artifact.id] = artifact
        return artifact

    async def generate_batch(self, artifact_plan: dict, content: str,
                             conversation_id: str = "",
                             project_id: str = "") -> list[Artifact]:
        """批量生成成果物（并行）

        Args:
            artifact_plan: OutputRouter 返回的计划
            content: AI 回答内容
            conversation_id: 会话ID
            project_id: 项目ID

        Returns:
            成果物列表
        """
        artifacts_to_generate = artifact_plan.get("artifacts", [])
        if not artifacts_to_generate:
            return []

        # 限制同时生成的数量
        max_parallel = 3
        tasks = []
        for item in artifacts_to_generate[:max_parallel]:
            task = self.generate(
                artifact_type=item["type"],
                content=content,
                title=item.get("title", ""),
                conversation_id=conversation_id,
                project_id=project_id,
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        artifacts = []
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Batch generation error: {r}")
                artifacts.append(Artifact(status="failed", error=str(r)[:200]))
            else:
                artifacts.append(r)

        return artifacts

    async def generate_background(self, artifact_plan: dict, content: str,
                                   conversation_id: str = "",
                                   project_id: str = ""):
        """后台生成成果物（不阻塞聊天响应）

        用 asyncio.create_task 启动，完成后通过 WebSocket 通知前端
        """
        try:
            artifacts = await self.generate_batch(
                artifact_plan, content, conversation_id, project_id
            )
            # 通知前端（通过 events 或 WebSocket）
            logger.info(f"Background artifacts generated: {len(artifacts)} items")
            return artifacts
        except Exception as e:
            logger.error(f"Background generation failed: {e}", exc_info=True)
            return []

    def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        return self._registry.get(artifact_id)

    def list_artifacts(self, conversation_id: str = "",
                       project_id: str = "") -> list[Artifact]:
        """列出成果物"""
        results = list(self._registry.values())
        if conversation_id:
            results = [a for a in results if a.conversation_id == conversation_id]
        if project_id:
            results = [a for a in results if a.project_id == project_id]
        return sorted(results, key=lambda a: a.created_at, reverse=True)

    def delete_artifact(self, artifact_id: str) -> bool:
        """删除成果物（文件 + 记录）"""
        artifact = self._registry.pop(artifact_id, None)
        if not artifact:
            return False
        try:
            if artifact.filepath and os.path.exists(artifact.filepath):
                os.remove(artifact.filepath)
        except Exception as e:
            logger.warning(f"Failed to delete artifact file: {e}")
        return True


# 全局单例
artifact_engine = ArtifactEngine()

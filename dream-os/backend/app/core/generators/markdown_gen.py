"""Markdown 生成器 — 生成 .md 文件"""
from pathlib import Path
from .base import BaseGenerator


class MarkdownGenerator(BaseGenerator):
    supported_types = ["markdown", "markdown_table", "api_doc", "speech", "txt"]

    async def generate(self, content: str, output_path: Path,
                       title: str = "", **kwargs) -> dict:
        self._ensure_dir(output_path)
        artifact_type = kwargs.get("artifact_type", output_path.suffix.lstrip("."))

        if artifact_type == "markdown_table":
            md_content = self._format_as_table(content, title)
        elif artifact_type == "api_doc":
            md_content = self._format_api_doc(content, title)
        elif artifact_type == "speech":
            md_content = self._format_speech(content, title)
        elif artifact_type == "txt":
            md_content = content
            output_path = output_path.with_suffix(".txt")
        else:
            md_content = self._format_markdown(content, title)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        return {"success": True}

    def _format_markdown(self, content: str, title: str) -> str:
        parts = []
        if title:
            parts.append(f"# {title}\n")
        parts.append(content)
        return "\n\n".join(parts)

    def _format_as_table(self, content: str, title: str) -> str:
        parts = []
        if title:
            parts.append(f"# {title}\n")
        # 尝试将内容转为表格
        lines = content.strip().split("\n")
        table_lines = []
        for line in lines:
            if "|" in line:
                table_lines.append(line)
            elif "-" in line and line.strip().startswith("-"):
                table_lines.append("| --- | --- |")
            elif ":" in line:
                parts_table = line.split(":", 1)
                table_lines.append(f"| {parts_table[0].strip()} | {parts_table[1].strip()} |")

        if table_lines:
            parts.append("| 项目 | 内容 |\n| --- | --- |")
            parts.extend(table_lines)
        else:
            parts.append(content)

        return "\n".join(parts)

    def _format_api_doc(self, content: str, title: str) -> str:
        parts = [f"# API Documentation\n"]
        if title:
            parts.append(f"## {title}\n")
        parts.append(content)
        return "\n\n".join(parts)

    def _format_speech(self, content: str, title: str) -> str:
        parts = [f"# 演讲稿\n"]
        if title:
            parts.append(f"## {title}\n")
        parts.append(content)
        return "\n\n".join(parts)

"""Mermaid 图表生成器 — 生成 .mmd 文件（流程图/思维导图/架构图等）"""
from pathlib import Path
from .base import BaseGenerator


class MermaidGenerator(BaseGenerator):
    supported_types = ["mermaid", "mindmap", "flowchart", "architecture",
                       "er_diagram", "sequence_diagram", "gantt", "org_chart"]

    async def generate(self, content: str, output_path: Path,
                       title: str = "", **kwargs) -> dict:
        self._ensure_dir(output_path)
        artifact_type = kwargs.get("artifact_type", "mermaid")

        mermaid_content = self._generate_mermaid(content, title, artifact_type)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(mermaid_content)
        return {"success": True}

    def _generate_mermaid(self, content: str, title: str, artifact_type: str) -> str:
        generators = {
            "mindmap": self._gen_mindmap,
            "flowchart": self._gen_flowchart,
            "architecture": self._gen_architecture,
            "er_diagram": self._gen_er,
            "sequence_diagram": self._gen_sequence,
            "gantt": self._gen_gantt,
            "org_chart": self._gen_org_chart,
            "mermaid": self._gen_flowchart,
        }
        gen_func = generators.get(artifact_type, self._gen_flowchart)
        return gen_func(content, title)

    def _gen_mindmap(self, content: str, title: str) -> str:
        """生成思维导图"""
        lines = content.strip().split("\n")
        root = title or "主题"
        parts = [f"mindmap", f"  root(({root}))"]

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("---"):
                continue
            # 提取关键点
            clean = line.lstrip("-•*0-9. ")
            if clean:
                # 判断层级
                if line.startswith("  "):
                    parts.append(f"    {clean}")
                else:
                    parts.append(f"  {clean}")

        return "\n".join(parts)

    def _gen_flowchart(self, content: str, title: str) -> str:
        """生成流程图"""
        lines = content.strip().split("\n")
        parts = [f"flowchart TD"]
        prev_id = None

        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("---"):
                continue
            clean = line.lstrip("-•*0-9.→ ")
            if clean:
                node_id = f"N{i}"
                parts.append(f"  {node_id}[\"{clean}\"]")
                if prev_id:
                    parts.append(f"  {prev_id} --> {node_id}")
                prev_id = node_id

        return "\n".join(parts)

    def _gen_architecture(self, content: str, title: str) -> str:
        """生成架构图"""
        lines = content.strip().split("\n")
        parts = [f"flowchart TB"]

        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("---"):
                continue
            clean = line.lstrip("-•*0-9. ")
            if ":" in clean:
                name, desc = clean.split(":", 1)
                parts.append(f"  M{i}[\"{name.strip()}\"]")
                parts.append(f"  D{i}[\"{desc.strip()}\"]")
                parts.append(f"  M{i} --> D{i}")
            elif clean:
                parts.append(f"  M{i}[\"{clean}\"]")

        # 连接模块
        for i in range(len(parts)):
            if i + 1 < len(parts) and f"M{i}[" in parts[i] and f"M{i+1}[" in parts[i+1]:
                if f"M{i} -->" not in parts[i]:
                    parts.append(f"  M{i} --> M{i+1}")

        return "\n".join(parts)

    def _gen_er(self, content: str, title: str) -> str:
        """生成 ER 图"""
        return f"erDiagram\n  ENTITY {{\n    string id\n    string name\n  }}\n  ENTITY ||--o{{ ENTITY : has"

    def _gen_sequence(self, content: str, title: str) -> str:
        """生成时序图"""
        return f"sequenceDiagram\n  participant User\n  participant System\n  User->>System: 请求\n  System-->>User: 响应"

    def _gen_gantt(self, content: str, title: str) -> str:
        """生成甘特图"""
        lines = content.strip().split("\n")
        parts = [f"gantt", f"  title {title or '项目计划'}", f"  dateFormat YYYY-MM-DD"]

        task_num = 0
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("---"):
                continue
            clean = line.lstrip("-•*0-9. ")
            if clean:
                task_num += 1
                parts.append(f"  任务{task_num} : a{task_num}, {task_num}d")

        return "\n".join(parts)

    def _gen_org_chart(self, content: str, title: str) -> str:
        """生成组织架构图"""
        return f"flowchart TD\n  CEO[CEO]\n  CTO[CTO]\n  CFO[CFO]\n  CEO --> CTO\n  CEO --> CFO"

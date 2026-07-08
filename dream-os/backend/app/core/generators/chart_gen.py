"""图表生成器 — 生成 SVG 图表（柱状图/折线图/饼图等）"""
import json
from pathlib import Path
from .base import BaseGenerator


class ChartGenerator(BaseGenerator):
    supported_types = ["bar_chart", "line_chart", "pie_chart",
                       "radar_chart", "trend_chart"]

    async def generate(self, content: str, output_path: Path,
                       title: str = "", **kwargs) -> dict:
        self._ensure_dir(output_path)
        artifact_type = kwargs.get("artifact_type", "bar_chart")

        svg_content = self._generate_chart(content, title, artifact_type)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        return {"success": True}

    def _generate_chart(self, content: str, title: str, chart_type: str) -> str:
        """生成 SVG 图表"""
        data = self._extract_data(content)
        generators = {
            "bar_chart": self._gen_bar,
            "line_chart": self._gen_line,
            "pie_chart": self._gen_pie,
            "radar_chart": self._gen_radar,
            "trend_chart": self._gen_line,
        }
        gen_func = generators.get(chart_type, self._gen_bar)
        return gen_func(data, title or chart_type)

    def _extract_data(self, content: str) -> list[tuple[str, float]]:
        """从内容中提取数据点"""
        data = []
        for line in content.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # 尝试提取 "名称: 数值" 格式
            if ":" in line or "：" in line:
                sep = ":" if ":" in line else "："
                parts = line.split(sep, 1)
                label = parts[0].strip().lstrip("-•*0-9. ")
                try:
                    value = float(parts[1].strip().replace(",", "").replace("%", ""))
                    data.append((label, value))
                except ValueError:
                    continue
            elif "|" in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2:
                    try:
                        value = float(parts[-1].replace(",", "").replace("%", ""))
                        data.append((parts[0], value))
                    except ValueError:
                        continue

        # 如果没有提取到数据，生成示例数据
        if not data:
            data = [("项目1", 75), ("项目2", 50), ("项目3", 90), ("项目4", 60)]

        return data

    def _gen_bar(self, data: list[tuple[str, float]], title: str) -> str:
        """生成柱状图 SVG"""
        width, height = 600, 400
        margin = 60
        chart_w = width - 2 * margin
        chart_h = height - 2 * margin
        max_val = max(d[1] for d in data) if data else 100
        bar_w = min(60, chart_w // max(len(data), 1) - 10)

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
            f'<style>text{{font-family:system-ui;font-size:12px;fill:#808090}}'
            f'.title{{font-size:16px;font-weight:bold;fill:#e8e8f0}}</style>',
            f'<rect width="100%" height="100%" fill="#12121c" rx="8"/>',
            f'<text x="{width//2}" y="30" text-anchor="middle" class="title">{title}</text>',
        ]

        # Y轴
        svg_parts.append(f'<line x1="{margin}" y1="{margin}" x2="{margin}" '
                         f'y2="{height-margin}" stroke="#333" stroke-width="1"/>')
        svg_parts.append(f'<line x1="{margin}" y1="{height-margin}" '
                         f'x2="{width-margin}" stroke="#333" stroke-width="1"/>')

        # 柱子
        colors = ["#6c5ce7", "#00cec9", "#fd79a8", "#fdcb6e", "#e17055", "#0984e3"]
        for i, (label, value) in enumerate(data):
            x = margin + 20 + i * (chart_w // max(len(data), 1))
            bar_h = int((value / max_val) * chart_h * 0.9)
            y = height - margin - bar_h
            color = colors[i % len(colors)]
            svg_parts.append(f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bar_h}" '
                             f'fill="{color}" rx="4" opacity="0.9"/>')
            svg_parts.append(f'<text x="{x + bar_w//2}" y="{height-margin+18}" '
                             f'text-anchor="middle">{label[:6]}</text>')
            svg_parts.append(f'<text x="{x + bar_w//2}" y="{y-5}" '
                             f'text-anchor="middle" fill="{color}">{value}</text>')

        svg_parts.append('</svg>')
        return "\n".join(svg_parts)

    def _gen_line(self, data: list[tuple[str, float]], title: str) -> str:
        """生成折线图 SVG"""
        width, height = 600, 400
        margin = 60
        chart_w = width - 2 * margin
        chart_h = height - 2 * margin
        max_val = max(d[1] for d in data) if data else 100

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
            f'<style>text{{font-family:system-ui;font-size:12px;fill:#808090}}'
            f'.title{{font-size:16px;font-weight:bold;fill:#e8e8f0}}</style>',
            f'<rect width="100%" height="100%" fill="#12121c" rx="8"/>',
            f'<text x="{width//2}" y="30" text-anchor="middle" class="title">{title}</text>',
        ]

        # 轴线
        svg_parts.append(f'<line x1="{margin}" y1="{margin}" x2="{margin}" '
                         f'y2="{height-margin}" stroke="#333" stroke-width="1"/>')
        svg_parts.append(f'<line x1="{margin}" y1="{height-margin}" '
                         f'x2="{width-margin}" stroke="#333" stroke-width="1"/>')

        # 数据点和连线
        if data:
            points = []
            for i, (label, value) in enumerate(data):
                x = margin + int(i * chart_w / max(len(data) - 1, 1))
                y = height - margin - int((value / max_val) * chart_h * 0.9)
                points.append((x, y))
                svg_parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#00cec9"/>')
                svg_parts.append(f'<text x="{x}" y="{height-margin+18}" '
                                 f'text-anchor="middle">{label[:6]}</text>')

            # 连线
            path = " ".join(f"L{x},{y}" for x, y in points)
            svg_parts.append(f'<path d="M{points[0][0]},{points[0][1]} {path}" '
                             f'fill="none" stroke="#00cec9" stroke-width="2"/>')

        svg_parts.append('</svg>')
        return "\n".join(svg_parts)

    def _gen_pie(self, data: list[tuple[str, float]], title: str) -> str:
        """生成饼图 SVG"""
        import math
        width, height = 500, 400
        cx, cy = 200, 200
        r = 140

        total = sum(d[1] for d in data) if data else 1
        colors = ["#6c5ce7", "#00cec9", "#fd79a8", "#fdcb6e", "#e17055", "#0984e3", "#a29bfe"]

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
            f'<style>text{{font-family:system-ui;font-size:11px;fill:#e8e8f0}}</style>',
            f'<rect width="100%" height="100%" fill="#12121c" rx="8"/>',
            f'<text x="{cx}" y="30" text-anchor="middle" '
            f'style="font-size:16px;font-weight:bold">{title}</text>',
        ]

        angle = 0
        for i, (label, value) in enumerate(data):
            pct = value / total
            sweep = pct * 360
            x1 = cx + r * math.cos(math.radians(angle))
            y1 = cy + r * math.sin(math.radians(angle))
            x2 = cx + r * math.cos(math.radians(angle + sweep))
            y2 = cy + r * math.sin(math.radians(angle + sweep))
            large_arc = 1 if sweep > 180 else 0
            color = colors[i % len(colors)]

            svg_parts.append(
                f'<path d="M{cx},{cy} L{x1},{y1} A{r},{r} 0 {large_arc},1 {x2},{y2} Z" '
                f'fill="{color}" opacity="0.85"/>'
            )

            # 图例
            ly = 50 + i * 22
            svg_parts.append(f'<rect x="{cx+r+30}" y="{ly}" width="14" height="14" '
                             f'fill="{color}" rx="2"/>')
            svg_parts.append(f'<text x="{cx+r+50}" y="{ly+12}">'
                             f'{label[:8]} ({pct*100:.0f}%)</text>')

            angle += sweep

        svg_parts.append('</svg>')
        return "\n".join(svg_parts)

    def _gen_radar(self, data: list[tuple[str, float]], title: str) -> str:
        """生成雷达图 SVG（简化版）"""
        return self._gen_bar(data, title)

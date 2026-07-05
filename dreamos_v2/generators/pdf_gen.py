"""PDF 生成器 — 生成 .pdf 文件"""
from pathlib import Path
from . import BaseGenerator


class PdfGenerator(BaseGenerator):
    supported_types = ["pdf"]

    async def generate(self, content: str, output_path: Path,
                       title: str = "", **kwargs) -> dict:
        self._ensure_dir(output_path)

        # 尝试使用 reportlab
        try:
            return await self._gen_with_reportlab(content, output_path, title)
        except ImportError:
            pass

        # 降级：生成 HTML 格式的伪 PDF（浏览器可打印为 PDF）
        try:
            return await self._gen_html_pdf(content, output_path, title)
        except Exception as e:
            # 最终降级：直接保存文本
            txt_path = output_path.with_suffix(".txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(f"{title}\n{'='*40}\n\n{content}")
            return {"success": True, "fallback": "txt"}

    async def _gen_with_reportlab(self, content: str, output_path: Path,
                                   title: str) -> dict:
        """使用 reportlab 生成真正的 PDF"""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        doc = SimpleDocTemplate(str(output_path), pagesize=A4)
        styles = getSampleStyleSheet()

        # 尝试注册中文字体
        font_name = "Helvetica"
        try:
            pdfmetrics.registerFont(TTFont('Chinese', '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'))
            font_name = 'Chinese'
        except Exception:
            try:
                pdfmetrics.registerFont(TTFont('Chinese', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'))
                font_name = 'Chinese'
            except Exception:
                pass

        # 自定义样式
        title_style = ParagraphStyle(
            'CustomTitle', parent=styles['Title'],
            fontName=font_name, fontSize=18, spaceAfter=20,
        )
        body_style = ParagraphStyle(
            'CustomBody', parent=styles['Normal'],
            fontName=font_name, fontSize=11, leading=18,
            spaceAfter=8,
        )

        elements = []
        if title:
            elements.append(Paragraph(title, title_style))
            elements.append(Spacer(1, 12))

        # 段落处理
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                elements.append(Spacer(1, 6))
                continue
            # 转义 HTML 特殊字符
            line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if line.startswith("# "):
                elements.append(Paragraph(line[2:], title_style))
            else:
                elements.append(Paragraph(line, body_style))

        doc.build(elements)
        return {"success": True}

    async def _gen_html_pdf(self, content: str, output_path: Path,
                             title: str) -> dict:
        """生成可打印为 PDF 的 HTML"""
        html_path = output_path.with_suffix(".html")
        html_content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title or 'Document'}</title>
<style>
body {{ font-family: -apple-system, 'Segoe UI', system-ui, sans-serif;
       max-width: 800px; margin: 40px auto; padding: 20px;
       line-height: 1.8; color: #333; }}
h1 {{ color: #6c5ce7; border-bottom: 2px solid #6c5ce7; padding-bottom: 10px; }}
h2 {{ color: #00cec9; }}
h3 {{ color: #fd79a8; }}
table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
th {{ background: #6c5ce7; color: white; }}
@media print {{ body {{ margin: 0; }} }}
</style></head><body>
<h1>{title or 'Document'}</h1>
<div style="white-space: pre-wrap; font-size: 14px;">{content}</div>
</body></html>"""

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return {"success": True, "fallback": "html_printable"}

"""Browser Tool — 网页浏览/抓取工具"""
import json
import logging
from ..tools.base import BaseTool, ToolResult

logger = logging.getLogger("dream-os.tools.browser")


class BrowserTool(BaseTool):
    """网页浏览工具 — 获取网页内容"""

    name = "browser_fetch"
    description = "浏览网页、获取网页内容（HTML 文本提取）"

    async def execute(self, command: str, **kwargs) -> ToolResult:
        """执行网页浏览

        command 格式:
            browser:https://example.com
        """
        try:
            url = command.replace("browser:", "").strip()
            if not url:
                return ToolResult(success=False, stderr="请提供要访问的 URL")
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url
            return await self._fetch_page(url)
        except Exception as e:
            logger.error(f"Browser fetch failed: {e}")
            return ToolResult(
                success=False,
                stderr=f"网页访问失败: {str(e)[:200]}",
                exit_code=1,
            )

    async def _fetch_page(self, url: str) -> ToolResult:
        """获取网页内容"""
        import httpx
        import re

        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        ) as client:
            response = await client.get(url)
            content = response.text

            # 提取文本内容（去除 HTML 标签）
            text = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            text = text[:5000]  # 限制输出长度

            result = json.dumps({
                "url": str(response.url),
                "status_code": response.status_code,
                "title": self._extract_title(content),
                "content_preview": text[:3000],
                "content_length": len(text),
            }, ensure_ascii=False)

            return ToolResult(success=True, stdout=result)

    @staticmethod
    def _extract_title(html: str) -> str:
        import re
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.I)
        return m.group(1).strip() if m else ""
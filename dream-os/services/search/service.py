"""Search Service - 搜索服务"""
from ..base import BaseService


class SearchService(BaseService):
    name = "search"
    version = "1.0.0"

    async def initialize(self):
        try:
            import httpx
            self._search_available = True
        except ImportError:
            self._search_available = False
        return self

    async def search(self, query, engine="auto"):
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "http://searxng:8080/search",
                    params={"q": query, "format": "json"},
                )
                data = resp.json()
                results = data.get("results", [])
                return {
                    "query": query,
                    "results": [
                        {"title": r.get("title", ""), "url": r.get("url", ""),
                         "content": r.get("content", "")[:200]}
                        for r in results[:10]
                    ],
                    "count": len(results),
                }
        except Exception as e:
            return {"query": query, "error": str(e)[:200], "results": []}

    async def health_check(self):
        return {
            "name": self.name,
            "status": "healthy" if getattr(self, "_search_available", False) else "degraded",
            "version": self.version,
        }
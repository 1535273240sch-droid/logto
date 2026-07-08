"""Stock Tool — 股票/基金/加密货币/黄金 实时行情查询"""
import json, logging, httpx
from ..tools.base import BaseTool, ToolResult

logger = logging.getLogger("dream-os.tools.stock")

STOCK_API = "https://qt.gtimg.cn/q="
CRYPTO_API = "https://api.coingecko.com/api/v3/simple/price"


class StockTool(BaseTool):
    name = "stock_query"
    description = "查询股票、基金、加密货币、黄金白银的实时行情"

    async def execute(self, command: str, **kwargs) -> ToolResult:
        cmd = command.strip().lower()
        try:
            if cmd.startswith("crypto:"):
                return await self._query_crypto(cmd.replace("crypto:", "").strip())
            elif "黄金" in cmd or "金价" in cmd or cmd.startswith("gold"):
                return await self._query_gold()
            elif "白银" in cmd or "银价" in cmd or cmd.startswith("silver"):
                return await self._query_gold("XAG")
            else:
                code = cmd.replace("stock:", "").strip()
                return await self._query_stock(code)
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return ToolResult(success=False, stderr=f"查询失败: {str(e)[:200]}", exit_code=1)

    async def _query_gold(self, symbol: str = "XAU") -> ToolResult:
        name_map = {"XAU": "黄金", "XAG": "白银"}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"https://api.gold-api.com/price/{symbol}")
                if resp.status_code == 200:
                    data = resp.json()
                    result = json.dumps({
                        "name": name_map.get(symbol, symbol),
                        "price": data.get("price", "N/A"),
                        "currency": data.get("currency", "USD"),
                        "change_24h": data.get("ch", "N/A"),
                        "update_time": data.get("timestamp", ""),
                    }, ensure_ascii=False)
                    return ToolResult(success=True, stdout=result)
                return ToolResult(success=False, stderr=f"查询失败: HTTP {resp.status_code}")
        except Exception as e:
            return ToolResult(success=False, stderr=f"查询异常: {str(e)[:200]}")

    async def _query_stock(self, code: str) -> ToolResult:
        fmt_code = self._format_code(code)
        url = f"{STOCK_API}{fmt_code}"
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url)
            text = response.text
            if "~" in text:
                parts = text.split("~")
                if len(parts) > 40:
                    result = json.dumps({
                        "code": code, "name": parts[1], "price": parts[3],
                        "change": parts[31], "change_pct": parts[32],
                        "open": parts[5], "high": parts[33], "low": parts[34],
                        "volume": parts[6], "turnover": parts[37],
                        "currency": "HKD" if "hk" in parts[0].lower() else "CNY" if "sh" in parts[0].lower() or "sz" in parts[0].lower() else "USD",
                    }, ensure_ascii=False)
                    return ToolResult(success=True, stdout=result)
                return ToolResult(success=True, stdout=text[:2000])
            return ToolResult(success=False, stderr=f"无法解析: {text[:200]}")

    async def _query_crypto(self, coin_id: str) -> ToolResult:
        url = f"{CRYPTO_API}?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url)
            data = response.json()
            if coin_id in data:
                coin = data[coin_id]
                result = json.dumps({"coin": coin_id, "price_usd": coin.get("usd", "N/A"), "change_24h": coin.get("usd_24h_change", "N/A"), "currency": "USD"}, ensure_ascii=False)
                return ToolResult(success=True, stdout=result)
            return ToolResult(success=False, stderr=f"未找到: {coin_id}")

    @staticmethod
    def _format_code(code: str) -> str:
        code = code.upper().strip()
        if code.endswith(".HK"): return f"hk{code.replace('.HK', '')}"
        if not code.endswith(".SH") and not code.endswith(".SZ"): return code
        suffix = code[-2:].lower(); num = code.replace(f".{suffix.upper()}", "")
        return f"{suffix}{num}"

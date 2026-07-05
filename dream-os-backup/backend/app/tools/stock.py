"""Stock Tool — 股票/基金/加密货币实时行情查询"""
import json
import logging
from ..tools.base import BaseTool, ToolResult

logger = logging.getLogger("dream-os.tools.stock")

# 免费股票 API 端点
STOCK_API = "https://qt.gtimg.cn/q="  # 腾讯股票行情接口
CRYPTO_API = "https://api.coingecko.com/api/v3/simple/price"


class StockTool(BaseTool):
    """股票/基金/加密货币行情查询工具"""

    name = "stock_query"
    description = "查询股票、基金、加密货币的实时行情（价格、涨跌幅、成交量）"

    async def execute(self, command: str, **kwargs) -> ToolResult:
        """执行股票查询

        command 格式:
            stock:0700.HK      — 腾讯港股
            stock:9988.HK      — 阿里港股
            stock:AAPL         — 苹果美股
            stock:600519.SH    — 茅台A股
            crypto:bitcoin     — 比特币
            crypto:ethereum    — 以太坊
        """
        cmd = command.strip().lower()

        try:
            if cmd.startswith("crypto:"):
                return await self._query_crypto(cmd.replace("crypto:", "").strip())
            else:
                code = cmd.replace("stock:", "").strip()
                return await self._query_stock(code)
        except Exception as e:
            logger.error(f"Stock query failed: {e}")
            return ToolResult(
                success=False,
                stderr=f"股票查询失败: {str(e)[:200]}",
                exit_code=1,
            )

    async def _query_stock(self, code: str) -> ToolResult:
        """查询股票行情"""
        import httpx

        # 格式化股票代码
        fmt_code = self._format_code(code)
        url = f"{STOCK_API}{fmt_code}"

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url)
            text = response.text

            # 解析腾讯行情接口返回
            if "~" in text:
                parts = text.split("~")
                if len(parts) > 40:
                    name = parts[1]
                    price = parts[3]
                    change_pct = parts[32]
                    change = parts[31]
                    high = parts[33]
                    low = parts[34]
                    volume = parts[6]
                    turnover = parts[37]
                    open_price = parts[5]
                    market = parts[0].split("_")[-1] if "_" in parts[0] else ""

                    result = json.dumps({
                        "code": code,
                        "name": name,
                        "price": price,
                        "change": change,
                        "change_pct": change_pct,
                        "open": open_price,
                        "high": high,
                        "low": low,
                        "volume": volume,
                        "turnover": turnover,
                        "market": "港股" if "hk" in market.lower() else "A股" if "sh" in market.lower() or "sz" in market.lower() else "美股",
                        "currency": "HKD" if "hk" in market.lower() else "CNY" if "sh" in market.lower() or "sz" in market.lower() else "USD",
                    }, ensure_ascii=False)

                    return ToolResult(success=True, stdout=result)
                else:
                    # 尝试普通文本解析
                    return ToolResult(success=True, stdout=text[:2000])
            else:
                return ToolResult(success=False, stderr=f"无法解析股票数据: {text[:200]}")

    async def _query_crypto(self, coin_id: str) -> ToolResult:
        """查询加密货币价格"""
        import httpx

        url = f"{CRYPTO_API}?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url)
            data = response.json()

            if coin_id in data:
                coin = data[coin_id]
                result = json.dumps({
                    "coin": coin_id,
                    "price_usd": coin.get("usd", "N/A"),
                    "change_24h": coin.get("usd_24h_change", "N/A"),
                    "currency": "USD",
                }, ensure_ascii=False)
                return ToolResult(success=True, stdout=result)
            else:
                return ToolResult(success=False, stderr=f"未找到加密货币: {coin_id}")

    @staticmethod
    def _format_code(code: str) -> str:
        """格式化股票代码为腾讯行情接口格式"""
        code = code.upper().strip()
        # 港股: 0700.HK → hk0700
        if code.endswith(".HK"):
            return f"hk{code.replace('.HK', '')}"
        # 美股: AAPL → 直接使用
        if not code.endswith(".SH") and not code.endswith(".SZ"):
            return code
        # A股: 600519.SH → sh600519
        suffix = code[-2:].lower()
        num = code.replace(f".{suffix.upper()}", "")
        return f"{suffix}{num}"
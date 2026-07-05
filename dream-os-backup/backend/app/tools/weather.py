"""Weather Tool — 天气查询工具"""
import json
import logging
from ..tools.base import BaseTool, ToolResult

logger = logging.getLogger("dream-os.tools.weather")


class WeatherTool(BaseTool):
    """天气查询工具 — 查询城市实时天气"""

    name = "weather_query"
    description = "查询城市实时天气（温度、湿度、风速、天气状况）"

    async def execute(self, command: str, **kwargs) -> ToolResult:
        """执行天气查询

        command 格式:
            weather:北京
            weather:Shanghai
        """
        try:
            city = command.replace("weather:", "").strip()
            if not city:
                return ToolResult(success=False, stderr="请指定要查询的城市")
            return await self._query_weather(city)
        except Exception as e:
            logger.error(f"Weather query failed: {e}")
            return ToolResult(
                success=False,
                stderr=f"天气查询失败: {str(e)[:200]}",
                exit_code=1,
            )

    async def _query_weather(self, city: str) -> ToolResult:
        """查询城市天气"""
        import httpx

        # 使用 wttr.in 免费天气 API
        url = f"https://wttr.in/{city}?format=j1"

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url)
            data = response.json()

            current = data.get("current_condition", [{}])[0]
            location = data.get("nearest_area", [{}])[0]

            city_name = location.get("areaName", [{}])[0].get("value", city)
            country = location.get("country", [{}])[0].get("value", "")
            region = location.get("region", [{}])[0].get("value", "")

            result = json.dumps({
                "city": city_name,
                "country": country,
                "region": region,
                "temp_C": current.get("temp_C", "N/A"),
                "feels_like_C": current.get("FeelsLikeC", "N/A"),
                "humidity": current.get("humidity", "N/A"),
                "weather_desc": current.get("weatherDesc", [{}])[0].get("value", ""),
                "wind_speed_kmh": current.get("windspeedKmph", "N/A"),
                "wind_dir": current.get("winddir16Point", "N/A"),
                "visibility_km": current.get("visibility", "N/A"),
                "pressure_mb": current.get("pressure", "N/A"),
                "uv_index": current.get("uvIndex", "N/A"),
                "observation_time": current.get("observation_time", ""),
            }, ensure_ascii=False)

            return ToolResult(success=True, stdout=result)
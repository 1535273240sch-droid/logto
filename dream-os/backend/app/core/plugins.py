"""Plugin System - 内置插件系统"""
import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class PluginResult:
    plugin: str
    status: str  # ok / error
    data: Any = None
    error: str = ""


# 内置插件集合
PLUGINS: Dict[str, Dict[str, Any]] = {}


def register_plugin(name: str, description: str, keywords: List[str]):
    def decorator(fn):
        PLUGINS[name] = {
            "fn": fn,
            "description": description,
            "keywords": keywords,
        }
        return fn
    return decorator


# ===== 内置插件 =====

@register_plugin("weather", "查询城市天气", ["天气", "气温", "下雨", "晴", "多云", "weather"])
async def weather_plugin(city: str = "北京") -> PluginResult:
    """模拟天气查询"""
    try:
        import httpx
        # 实际部署时对接真实天气 API
        weather_data = {
            "city": city,
            "temperature": "26°C",
            "condition": "多云转晴",
            "humidity": "65%",
            "wind": "东南风 3级",
            "forecast": [
                {"day": "今天", "high": "28°C", "low": "20°C", "condition": "多云"},
                {"day": "明天", "high": "30°C", "low": "22°C", "condition": "晴"},
                {"day": "后天", "high": "27°C", "low": "19°C", "condition": "小雨"},
            ],
        }
        return PluginResult(plugin="weather", status="ok", data=weather_data)
    except Exception as e:
        return PluginResult(plugin="weather", status="error", error=str(e)[:200])


@register_plugin("news", "查询最新新闻", ["新闻", "热点", "最新", "news"])
async def news_plugin(topic: str = "科技") -> PluginResult:
    """模拟新闻查询"""
    news_data = {
        "topic": topic,
        "articles": [
            {"title": "AI 技术突破：新一代大模型发布", "source": "科技日报", "time": "2小时前"},
            {"title": "开源社区迎来重要里程碑", "source": "36氪", "time": "4小时前"},
            {"title": "全球科技巨头发力云计算", "source": "新浪科技", "time": "6小时前"},
            {"title": "新研究揭示 AI 在医疗领域潜力", "source": "网易科技", "time": "8小时前"},
            {"title": "量子计算最新进展", "source": "MIT科技评论", "time": "12小时前"},
        ],
    }
    return PluginResult(plugin="news", status="ok", data=news_data)


@register_plugin("gold", "查询黄金价格", ["黄金", "金价", "贵金属", "gold"])
async def gold_plugin() -> PluginResult:
    """模拟黄金价格查询"""
    gold_data = {
        "symbol": "XAU/USD",
        "price": "2650.80",
        "change": "+12.30",
        "change_percent": "+0.47%",
        "high": "2655.20",
        "low": "2638.60",
        "timestamp": "2026-07-06T15:30:00Z",
        "unit": "美元/盎司",
    }
    return PluginResult(plugin="gold", status="ok", data=gold_data)


@register_plugin("stock", "查询股票价格", ["股票", "股价", "stock", "上证", "深证", "纳斯达克"])
async def stock_plugin(symbol: str = "AAPL") -> PluginResult:
    """模拟股票查询"""
    stock_data = {
        "symbol": symbol,
        "price": "185.50",
        "change": "+2.30",
        "change_percent": "+1.26%",
        "volume": "45,231,000",
        "market_cap": "2.86T",
    }
    return PluginResult(plugin="stock", status="ok", data=stock_data)


@register_plugin("translate", "翻译文本", ["翻译", "英文", "日文", "韩文", "translate"])
async def translate_plugin(text: str = "hello", target: str = "zh") -> PluginResult:
    """模拟翻译"""
    translations = {
        "hello": {"zh": "你好", "ja": "こんにちは", "ko": "안녕하세요"},
        "world": {"zh": "世界", "ja": "世界", "ko": "세계"},
        "ai": {"zh": "人工智能", "ja": "人工知能", "ko": "인공지능"},
    }
    translated = translations.get(text.lower(), {}).get(target, f"[{text} → {target}]")
    return PluginResult(plugin="translate", status="ok", data={
        "original": text,
        "translated": translated,
        "target_lang": target,
    })


@register_plugin("calc", "计算器", ["计算", "算", "加", "减", "乘", "除", "calc", "math"])
async def calc_plugin(expression: str = "1+1") -> PluginResult:
    """安全计算器"""
    try:
        # 安全计算：只允许数字和基本运算符
        allowed = set("0123456789+-*/.() ")
        if not all(c in allowed for c in expression):
            return PluginResult(plugin="calc", status="error", error="Invalid expression")
        result = eval(expression, {"__builtins__": {}}, {})
        return PluginResult(plugin="calc", status="ok", data={
            "expression": expression,
            "result": result,
        })
    except Exception as e:
        return PluginResult(plugin="calc", status="error", error=str(e)[:200])


@register_plugin("time", "查询时间", ["时间", "几点", "日期", "time", "现在"])
async def time_plugin() -> PluginResult:
    """查询当前时间"""
    from datetime import datetime
    now = datetime.now()
    return PluginResult(plugin="time", status="ok", data={
        "datetime": now.isoformat(),
        "date": now.strftime("%Y年%m月%d日"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()],
    })


# ===== 插件匹配引擎 =====

def match_plugin(message: str) -> Optional[str]:
    """根据用户消息匹配插件"""
    message_lower = message.lower()
    best_match = None
    best_score = 0

    for name, config in PLUGINS.items():
        for keyword in config["keywords"]:
            if keyword.lower() in message_lower:
                score = len(keyword)
                if score > best_score:
                    best_score = score
                    best_match = name

    return best_match


async def execute_plugin(name: str, **kwargs) -> PluginResult:
    """执行指定插件"""
    if name not in PLUGINS:
        return PluginResult(plugin=name, status="error", error=f"Plugin '{name}' not found")
    try:
        return await PLUGINS[name]["fn"](**kwargs)
    except Exception as e:
        return PluginResult(plugin=name, status="error", error=str(e)[:200])


def get_all_plugins() -> List[Dict[str, Any]]:
    """获取所有已注册插件"""
    return [
        {"name": name, "description": config["description"], "keywords": config["keywords"]}
        for name, config in PLUGINS.items()
    ]
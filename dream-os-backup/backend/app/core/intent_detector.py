"""Intent Detector — 意图识别器

识别用户意图并分类，确保 Planner 不猜、不跳步。
"""
import re
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("dream-os.intent")

# ── 意图类型 ──────────────────────────────

class IntentType:
    """所有支持的意图类型"""
    REAL_TIME_DATA = "real_time_data"      # 实时数据（股票、黄金、天气、新闻）
    FILE_OPERATION = "file_operation"       # 文件操作
    SHELL = "shell"                         # Shell 命令
    IMAGE = "image"                         # 图片生成
    MATH = "math"                           # 数学计算
    CODE = "code"                           # 代码编写
    SEARCH = "search"                       # 联网搜索/知识查询
    BROWSER = "browser"                     # 网页浏览
    CHAT = "chat"                           # 普通聊天
    MEMORY = "memory"                       # 记忆操作
    COMPLEX = "complex"                     # 复杂任务（多工具链）
    UNKNOWN = "unknown"                     # 未识别


@dataclass
class IntentResult:
    """意图识别结果"""
    intent_type: str
    confidence: float                # 0.0 ~ 1.0
    entities: dict = field(default_factory=dict)  # 提取的实体
    sub_intent: str = ""             # 子意图描述
    requires_context: bool = False   # 是否需要上下文
    context_hint: str = ""           # 上下文提示词


# ── 关键词规则 ──────────────────────────────

_INTENT_RULES = [
    # 实时数据 — 股票/基金
    (IntentType.REAL_TIME_DATA, 0.95, [
        r"股票",  # standalone stock query
        r"(?:股票|股价|行情|涨跌|市值|市盈率|市净率|收盘|开盘|涨幅|跌幅)",
        r"(?:黄金|白银|原油|石油|期货|现货|伦敦金|国际金价)",
        r"(?:汇率|外汇|美元|人民币|欧元|日元|英镑|港币)",
        r"(?:比特币|以太坊|eth|btc|加密货币|区块链|web3)",
        r"(?:腾讯|阿里|茅台|特斯拉|苹果|谷歌|亚马逊|英伟达|nvda|aapl|tsla|goog|amzn|baba|0700|9988)",
        r"(?:股价|现价|实时价格|多少钱一股|今天.*?行情)",
    ]),
    # 实时数据 — 天气
    (IntentType.REAL_TIME_DATA, 0.90, [
        r"(?:天气|温度|湿度|降雨|降雪|台风|空气质量|aqi|pm2[.]5)",
        r"(?:今天.*?天气|明天.*?天气|后天.*?天气|一周.*?天气)",
    ]),
    # 实时数据 — 新闻
    (IntentType.REAL_TIME_DATA, 0.85, [
        r"(?:新闻|热搜|头条|热榜|最新消息|今天.*?新闻|最新.*?资讯)",
    ]),
    # 搜索/知识查询
    (IntentType.SEARCH, 0.80, [
        r"(?:搜索|查一下|查查|查找|搜一下|搜搜|查询|百度|谷歌)",
        r"(?:什么是|什么是|是什么|是什么意思|怎么解释|如何理解)",
        r"(?:介绍|详情|说明|科普|概念|定义|含义)",
    ]),
    # Shell 命令
    (IntentType.SHELL, 0.95, [
        r"(?:执行|运行|操作|部署|安装|启动|停止|重启|配置|修改)",
        r"(?:查看.*?服务器|服务器.*?状态|系统.*?信息|磁盘.*?使用|内存.*?使用)",
        r"(?:创建.*?目录|创建.*?文件|删除.*?文件|复制.*?文件|移动.*?文件)",
        r"(?:docker|git |npm |pip |apt |yum |systemctl)",
        r"(?:df |free |ps |top |uptime |uname |hostname|whoami)",
    ]),
    # 文件操作
    (IntentType.FILE_OPERATION, 0.90, [
        r"(?:读取.*?文件|写入.*?文件|编辑.*?文件|保存.*?文件|打开.*?文件)",
        r"(?:创建.*?项目|新建.*?文件|列出.*?目录|查看.*?目录)",
    ]),
    # 图片生成
    (IntentType.IMAGE, 0.90, [
        r"(?:生成.*?图片|画.*?图|绘制|设计.*?海报|制作.*?logo|创建.*?图像)",
        r"(?:图片生成|文生图|ai.*?画|帮我画|给我画)",
    ]),
    # 数学计算
    (IntentType.MATH, 0.85, [
        r"(?:计算|多少个|等于|加|减|乘|除|求和|平均|统计|百分比)",
        r"(?:换算|转换|多少.*?平方|多少.*?立方|面积|体积)",
    ]),
    # 代码
    (IntentType.CODE, 0.80, [
        r"(?:写.*?代码|编写.*?函数|实现.*?功能|debug|调试|修复.*?bug)",
        r"(?:python|javascript|java|golang|rust|typescript|css|html)",
        r"(?:代码.*?review|代码.*?审查|代码.*?优化)",
    ]),
    # 记忆操作
    (IntentType.MEMORY, 0.85, [
        r"(?:记住|请记住|记下来|以后一直|以后都这样|不要忘记)",
        r"(?:回忆|之前.*?说过|之前.*?做过|回顾|历史)",
    ]),
    # 浏览器/网页
    (IntentType.BROWSER, 0.80, [
        r"(?:打开.*?网页|访问.*?网站|浏览|网页.*?内容|爬取|抓取)",
    ]),
    # 多工具链（复杂任务）
    (IntentType.COMPLEX, 0.70, [
        r"(?:分析|研究|调研|对比|比较|评估|总结|报告|趋势)",
        r"(?:生成.*?报告|输出.*?文档|整理.*?资料|汇总)",
    ]),
]

# 上下文关联词 — 表明需要参考上一条消息
_CONTEXT_KEYWORDS = [
    r"^(?:再|还|也|又|那|另外|顺便|同样|继续|接着)",
    r"^(?:it|he|she|they|this|that|these|those)",
    r"^(?:他|她|它|他们|她们|它们|这个|那个|这些|那些)",
    r"^(?:看看|查查|查一下|问一下|对比|比较)",
]


def detect_intent(text: str) -> IntentResult:
    """检测用户意图

    基于关键词规则匹配，不需要 AI 调用（轻量快速）。
    """
    if not text or not text.strip():
        return IntentResult(IntentType.CHAT, 0.5)

    text_clean = text.strip()

    # 检测是否需要上下文
    needs_context = False
    context_hint = ""
    for pattern in _CONTEXT_KEYWORDS:
        m = re.search(pattern, text_clean)
        if m:
            needs_context = True
            context_hint = f"开头'{m.group(0)}'表明可能引用前文"
            break

    # 检测是否为简单聊天
    simple_chat = _is_simple_chat(text_clean)
    if simple_chat:
        return IntentResult(
            IntentType.CHAT, 0.95,
            sub_intent="simple_chat",
            requires_context=needs_context,
            context_hint=context_hint,
        )

    # 遍历规则匹配意图
    best_intent = IntentType.UNKNOWN
    best_confidence = 0.0
    best_entities = {}

    for intent_type, confidence, patterns in _INTENT_RULES:
        for pattern in patterns:
            m = re.search(pattern, text_clean, re.I)
            if m:
                # 提取实体
                entity = m.group(0) if m.lastindex is None else m.group(1)
                entities = {"matched": entity, "keyword": pattern}

                # 特殊实体提取
                if intent_type == IntentType.REAL_TIME_DATA:
                    stock = _extract_stock(text_clean)
                    if stock:
                        entities["stock"] = stock
                    weather = _extract_weather(text_clean)
                    if weather:
                        entities["weather_city"] = weather

                if confidence > best_confidence:
                    best_intent = intent_type
                    best_confidence = confidence
                    best_entities = entities
                break

    # 兜底：如果包含"?"但没匹配到任何规则，可能是知识查询
    if best_confidence < 0.6 and (text_clean.endswith("?") or text_clean.endswith("？")):
        best_intent = IntentType.SEARCH
        best_confidence = 0.55

    logger.info(
        f"Intent: {best_intent} ({best_confidence:.2f}) "
        f"ctx={needs_context} "
        f"entities={best_entities}"
    )

    return IntentResult(
        best_intent, best_confidence,
        entities=best_entities,
        requires_context=needs_context,
        context_hint=context_hint,
    )


def _is_simple_chat(text: str) -> bool:
    """判断是否为简单对话"""
    chat_patterns = [
        "你好", "嗨", "hello", "hi", "hey",
        "谢谢", "感谢", "thanks", "thank",
        "再见", "拜拜", "bye",
        "你是谁", "你叫什么", "你能做什么",
        "在吗", "在不在", "好的", "ok", "行", "嗯",
        "哈哈", "呵呵", "好的谢谢", "可以",
    ]
    text_lower = text.strip().lower()
    if len(text) < 20 and any(p in text_lower for p in chat_patterns):
        # 避免"行"误匹配"行情"、"股票"等
        if len(text) >= 4:
            # 对较长文本，用词边界匹配
            import re
            for p in chat_patterns:
                if len(p) == 1:
                    # 单字模式（如"行"、"嗯"）只在短文本中匹配
                    if len(text) <= 4 and p in text_lower:
                        return True
                elif p in text_lower:
                    return True
            return False
        return True
    return False


def _extract_stock(text: str) -> Optional[str]:
    """提取股票代码或名称"""
    # 常见股票名称
    stocks = {
        "腾讯": "0700.HK", "阿里": "9988.HK", "阿里巴巴": "9988.HK",
        "茅台": "600519.SH", "特斯拉": "TSLA", "苹果": "AAPL",
        "谷歌": "GOOGL", "亚马逊": "AMZN", "英伟达": "NVDA",
        "百度": "BIDU", "京东": "JD", "拼多多": "PDD",
        "比亚迪": "1211.HK", "小米": "1810.HK", "美团": "3690.HK",
    }
    for name, code in stocks.items():
        if name in text:
            return name
    # 股票代码模式
    m = re.search(r"(\d{6}\.(?:SH|SZ|HK)|[A-Z]{1,5})", text)
    if m:
        return m.group(1)
    return None


def _extract_weather(text: str) -> Optional[str]:
    """提取天气查询的城市"""
    cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉",
              "南京", "天津", "重庆", "苏州", "西安", "长沙", "郑州",
              "东莞", "青岛", "沈阳", "宁波", "昆明", "大连", "厦门",
              "合肥", "佛山", "福州", "哈尔滨", "济南", "温州", "长春",
              "石家庄", "常州", "泉州", "南宁", "贵阳", "南昌", "太原",
              "烟台", "嘉兴", "南通", "金华", "珠海", "惠州", "徐州",
              "海口", "乌鲁木齐", "绍兴", "中山", "台州", "兰州"]
    for city in cities:
        if city in text:
            return city
    return None
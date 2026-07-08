"""Planner — 任务理解、拆解、制定执行计划"""
import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("dream-os.planner")


@dataclass
class PlanStep:
    """单个执行步骤"""
    step_id: int
    action: str          # 工具名或动作描述
    description: str     # 人类可读的描述
    tool: str = ""       # 实际调用的工具名
    tool_args: dict = field(default_factory=dict)
    depends_on: list[int] = field(default_factory=list)  # 依赖的步骤ID
    status: str = "pending"  # pending/running/done/failed


@dataclass
class ExecutionPlan:
    """完整执行计划"""
    task_summary: str          # 任务理解摘要
    steps: list[PlanStep]      # 步骤列表
    estimated_tools: list[str] # 预计使用的工具
    risk_level: str = "safe"   # safe/caution/dangerous

    def to_frontend(self) -> dict:
        return {
            "type": "plan",
            "task_summary": self.task_summary,
            "steps": [
                {
                    "step_id": s.step_id,
                    "action": s.action,
                    "description": s.description,
                    "tool": s.tool,
                    "depends_on": s.depends_on,
                    "status": s.status,
                }
                for s in self.steps
            ],
            "estimated_tools": self.estimated_tools,
            "risk_level": self.risk_level,
            "total_steps": len(self.steps),
        }


PLANNER_SYSTEM_PROMPT = """你是一个任务规划器。你的职责是分析用户需求并制定执行计划。

## 输出格式
你必须返回一个JSON对象，格式如下：
{
    "task_summary": "一句话概括用户要做什么",
    "risk_level": "safe" | "caution" | "dangerous",
    "steps": [
        {
            "step_id": 1,
            "action": "web_search",
            "description": "搜索最新数据",
            "tool": "http_fetch",
            "tool_args": {"command": "具体命令"},
            "depends_on": []
        }
    ],
    "estimated_tools": ["http_fetch", "shell_exec"]
}

## 可用工具
- shell_exec: 执行Linux命令（文件操作、系统查询、进程管理）
- http_fetch: HTTP请求（搜索、API调用、网页抓取）
- file_read: 读取文件内容
- file_write: 写入文件
- file_list: 列出目录文件
- stock_query: 股票/基金/加密货币行情查询（港股、A股、美股、加密货币）
- weather_query: 天气查询（城市实时天气）
- python_exec: 执行Python代码（数学计算、数据分析、图表生成）
- browser_fetch: 网页浏览/抓取（获取网页内容）
- image_generate: 图片生成（根据文字描述生成图片）

## 实时数据查询规则
- 用户问价格、股票、天气、黄金等 → 必须使用对应工具
- 不允许直接回答实时数据，必须调用工具
- 股票查询用 stock_query
- 天气查询用 weather_query
- 通用数据查询用 http_fetch

## 规划原则
1. 简单任务（问候、闲聊、常识问题）→ 0步，直接回答，不调用工具
2. 实时信息查询（天气、股价、新闻、服务器状态）→ 1-2步，调用工具
3. 操作类任务 → 2-5步，逐步执行
4. 复杂任务 → 分解为独立子任务
5. 每步只做一件事
6. 步骤之间有依赖关系的，标注depends_on
7. 危险操作标注risk_level为dangerous
8. 工具参数要具体可执行
9. 常识性问题（如历史人物、诗词作者、百科知识）不需要搜索，返回0步计划

## 示例
用户："帮我查一下今天比特币的价格"
{
    "task_summary": "查询比特币实时价格",
    "risk_level": "safe",
    "steps": [
        {
            "step_id": 1,
            "action": "web_search",
            "description": "查询比特币实时价格",
            "tool": "http_fetch",
            "tool_args": {"command": "GET https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"},
            "depends_on": []
        }
    ],
    "estimated_tools": ["http_fetch"]
}

用户："今天北京天气怎么样"
{
    "task_summary": "查询北京天气",
    "risk_level": "safe",
    "steps": [
        {
            "step_id": 1,
            "action": "weather_query",
            "description": "查询北京实时天气",
            "tool": "weather_query",
            "tool_args": {"command": "weather:北京"},
            "depends_on": []
        }
    ],
    "estimated_tools": ["weather_query"]
}

用户："腾讯股票多少钱"
{
    "task_summary": "查询腾讯股票价格",
    "risk_level": "safe",
    "steps": [
        {
            "step_id": 1,
            "action": "stock_query",
            "description": "查询腾讯股票行情",
            "tool": "stock_query",
            "tool_args": {"command": "stock:0700.HK"},
            "depends_on": []
        }
    ],
    "estimated_tools": ["stock_query"]
}

现在请为以下用户请求制定执行计划。只返回JSON，不要其他文字。"""


class Planner:
    """任务规划器 — 理解需求、拆解任务、生成计划"""

    def __init__(self):
        self.max_steps = 8

    async def plan(self, user_input: str, ai_client, model: str) -> ExecutionPlan:
        """
        分析用户输入，生成执行计划
        
        Args:
            user_input: 用户原始输入
            ai_client: OpenAI client
            model: 模型名称
        
        Returns:
            ExecutionPlan 对象
        """
        # 快速判断：简单对话不需要规划
        if self._is_simple_chat(user_input):
            return ExecutionPlan(
                task_summary=user_input[:60],
                steps=[],
                estimated_tools=[],
                risk_level="safe",
            )

        try:
            response = await ai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_input},
                ],
                temperature=0.2,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)

            steps = []
            for s in data.get("steps", []):
                steps.append(PlanStep(
                    step_id=s.get("step_id", len(steps) + 1),
                    action=s.get("action", ""),
                    description=s.get("description", ""),
                    tool=s.get("tool", ""),
                    tool_args=s.get("tool_args", {}),
                    depends_on=s.get("depends_on", []),
                ))

            plan = ExecutionPlan(
                task_summary=data.get("task_summary", user_input[:60]),
                steps=steps[:self.max_steps],
                estimated_tools=data.get("estimated_tools", []),
                risk_level=data.get("risk_level", "safe"),
            )

            logger.info(f"Plan generated: {plan.task_summary}, {len(plan.steps)} steps")
            return plan

        except Exception as e:
            logger.warning(f"Planner failed, fallback to direct execution: {e}")
            # 规划失败时，退回直接执行模式
            return ExecutionPlan(
                task_summary=user_input[:60],
                steps=[],
                estimated_tools=[],
                risk_level="safe",
            )

    def _is_simple_chat(self, text: str) -> bool:
        """判断是否为简单对话或常识问题，不需要规划"""
        text_lower = text.strip().lower()
        chat_patterns = [
            "你好", "嗨", "hello", "hi", "hey",
            "谢谢", "感谢", "thanks", "thank",
            "再见", "拜拜", "bye",
            "你是谁", "你叫什么", "你能做什么",
            "在吗", "在不在",
            "好的", "ok", "行", "嗯",
        ]
        # 短文本且匹配聊天模式
        if len(text) < 20 and any(p in text_lower for p in chat_patterns):
            # 避免"行"误匹配"行情"、"股票"等
            if len(text) >= 4:
                import re
                for p in chat_patterns:
                    if len(p) == 1:
                        if len(text) <= 4 and p in text_lower:
                            return True
                    elif p in text_lower:
                        return True
                return False
            return True
        # 常识问题模式（谁/什么/为什么/如何/什么时候，且无动作词和实时数据词）
        knowledge_patterns = ["是谁", "是什么", "为什么", "怎么样", "怎么做", "什么意思", "介绍一下"]
        action_words = ["查", "搜", "找", "做", "执行", "运行", "生成", "创建", "下载", "获取最新", "实时"]
        realtime_keywords = ["价格", "行情", "股价", "股票", "天气", "温度", "黄金", "比特币",
                           "汇率", "金价", "大盘", "走势", "涨", "跌", "市值",
                           "气温", "降水", "湿度", "风力", "风向"]
        # 如果包含实时数据关键词，绝对不可能是简单聊天
        if any(kw in text for kw in realtime_keywords):
            return False
        if any(p in text for p in knowledge_patterns) and not any(w in text for w in action_words):
            return True
        # 纯问题且无明确动作 — 排除实时数据查询
        if (text.endswith("?") or text.endswith("？")) and not any(w in text for w in action_words):
            return True
        return False

"""Output Router — 成果物输出路由

根据用户意图自动选择最优输出格式组合。
例如：旅游规划 → 行程表 + 思维导图 + PPT + PDF + 预算Excel
"""
import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

logger = logging.getLogger("dream-os.output_router")


class ArtifactType(str, Enum):
    """成果物类型"""
    # 文档类
    MARKDOWN = "markdown"
    WORD = "word"
    PDF = "pdf"
    HTML = "html"
    TXT = "txt"

    # 表格类
    EXCEL = "excel"
    CSV = "csv"
    MARKDOWN_TABLE = "markdown_table"

    # 演示类
    PPT = "ppt"
    SPEECH = "speech"

    # 图形类
    MERMAID = "mermaid"
    MINDMAP = "mindmap"
    FLOWCHART = "flowchart"
    ARCHITECTURE = "architecture"
    ER_DIAGRAM = "er_diagram"
    SEQUENCE_DIAGRAM = "sequence_diagram"
    GANTT = "gantt"
    ORG_CHART = "org_chart"

    # 数据可视化
    BAR_CHART = "bar_chart"
    LINE_CHART = "line_chart"
    PIE_CHART = "pie_chart"
    RADAR_CHART = "radar_chart"
    TREND_CHART = "trend_chart"

    # 代码类
    CODE = "code"
    API_DOC = "api_doc"


class OutputCategory(str, Enum):
    """输出类别"""
    DOCUMENT = "document"
    TABLE = "table"
    PRESENTATION = "presentation"
    DIAGRAM = "diagram"
    CHART = "chart"
    CODE = "code"


@dataclass
class ArtifactPlan:
    """成果物生成计划"""
    artifacts: list[dict] = field(default_factory=list)
    reasoning: str = ""

    def add(self, artifact_type: ArtifactType, category: OutputCategory,
            title: str = "", priority: int = 0, description: str = ""):
        self.artifacts.append({
            "type": artifact_type.value,
            "category": category.value,
            "title": title or artifact_type.value,
            "priority": priority,
            "description": description,
        })

    def sorted_artifacts(self) -> list[dict]:
        return sorted(self.artifacts, key=lambda x: x["priority"], reverse=True)

    def to_dict(self) -> dict:
        return {
            "artifacts": self.sorted_artifacts(),
            "count": len(self.artifacts),
            "reasoning": self.reasoning,
        }


# ── 意图 → 成果物映射表 ──────────────────────────────

INTENT_ARTIFACT_MAP = {
    "travel": {
        "artifacts": [
            (ArtifactType.EXCEL, OutputCategory.TABLE, "行程时间表", 10),
            (ArtifactType.MARKDOWN, OutputCategory.DOCUMENT, "每日安排", 9),
            (ArtifactType.MINDMAP, OutputCategory.DIAGRAM, "旅行思维导图", 8),
            (ArtifactType.PDF, OutputCategory.DOCUMENT, "旅行方案PDF", 7),
            (ArtifactType.PPT, OutputCategory.PRESENTATION, "旅行PPT", 5),
            (ArtifactType.EXCEL, OutputCategory.TABLE, "预算表", 6),
        ],
        "reasoning": "旅游规划适合输出行程表、每日安排、思维导图和预算表",
    },
    "business_plan": {
        "artifacts": [
            (ArtifactType.PPT, OutputCategory.PRESENTATION, "商业计划书PPT", 10),
            (ArtifactType.WORD, OutputCategory.DOCUMENT, "商业计划书Word", 9),
            (ArtifactType.MINDMAP, OutputCategory.DIAGRAM, "计划思维导图", 8),
            (ArtifactType.EXCEL, OutputCategory.TABLE, "财务预算表", 7),
            (ArtifactType.PDF, OutputCategory.DOCUMENT, "商业计划书PDF", 6),
            (ArtifactType.GANTT, OutputCategory.DIAGRAM, "实施甘特图", 5),
        ],
        "reasoning": "商业计划适合输出PPT、Word文档、财务预算和甘特图",
    },
    "stock_analysis": {
        "artifacts": [
            (ArtifactType.LINE_CHART, OutputCategory.CHART, "走势图", 10),
            (ArtifactType.EXCEL, OutputCategory.TABLE, "数据表", 9),
            (ArtifactType.PDF, OutputCategory.DOCUMENT, "分析报告PDF", 7),
            (ArtifactType.MARKDOWN, OutputCategory.DOCUMENT, "AI解读", 8),
            (ArtifactType.BAR_CHART, OutputCategory.CHART, "对比图", 6),
        ],
        "reasoning": "股票分析适合输出走势图、数据表和分析报告",
    },
    "study_plan": {
        "artifacts": [
            (ArtifactType.MINDMAP, OutputCategory.DIAGRAM, "知识思维导图", 10),
            (ArtifactType.EXCEL, OutputCategory.TABLE, "时间规划表", 9),
            (ArtifactType.PDF, OutputCategory.DOCUMENT, "学习计划PDF", 7),
            (ArtifactType.GANTT, OutputCategory.DIAGRAM, "学习甘特图", 6),
        ],
        "reasoning": "学习计划适合输出思维导图、时间规划和甘特图",
    },
    "software_dev": {
        "artifacts": [
            (ArtifactType.MERMAID, OutputCategory.DIAGRAM, "系统架构图", 10),
            (ArtifactType.FLOWCHART, OutputCategory.DIAGRAM, "流程图", 9),
            (ArtifactType.MARKDOWN, OutputCategory.DOCUMENT, "设计文档", 8),
            (ArtifactType.API_DOC, OutputCategory.DOCUMENT, "API文档", 7),
            (ArtifactType.ER_DIAGRAM, OutputCategory.DIAGRAM, "ER图", 6),
            (ArtifactType.SEQUENCE_DIAGRAM, OutputCategory.DIAGRAM, "时序图", 5),
        ],
        "reasoning": "软件开发适合输出架构图、流程图和设计文档",
    },
    "data_analysis": {
        "artifacts": [
            (ArtifactType.BAR_CHART, OutputCategory.CHART, "柱状图", 10),
            (ArtifactType.EXCEL, OutputCategory.TABLE, "数据表", 9),
            (ArtifactType.PIE_CHART, OutputCategory.CHART, "占比图", 8),
            (ArtifactType.PDF, OutputCategory.DOCUMENT, "分析报告", 7),
            (ArtifactType.MARKDOWN, OutputCategory.DOCUMENT, "分析总结", 6),
        ],
        "reasoning": "数据分析适合输出图表、数据表和分析报告",
    },
    "report": {
        "artifacts": [
            (ArtifactType.PDF, OutputCategory.DOCUMENT, "报告PDF", 10),
            (ArtifactType.WORD, OutputCategory.DOCUMENT, "报告Word", 9),
            (ArtifactType.PPT, OutputCategory.PRESENTATION, "汇报PPT", 8),
            (ArtifactType.MARKDOWN, OutputCategory.DOCUMENT, "报告Markdown", 5),
        ],
        "reasoning": "报告适合输出PDF、Word和PPT",
    },
    "meeting": {
        "artifacts": [
            (ArtifactType.MARKDOWN, OutputCategory.DOCUMENT, "会议纪要", 10),
            (ArtifactType.MINDMAP, OutputCategory.DIAGRAM, "讨论思维导图", 8),
            (ArtifactType.PDF, OutputCategory.DOCUMENT, "会议纪要PDF", 7),
            (ArtifactType.EXCEL, OutputCategory.TABLE, "行动项表", 9),
        ],
        "reasoning": "会议适合输出会议纪要、行动项和思维导图",
    },
}


# ── 关键词 → 意图映射 ──────────────────────────────

KEYWORD_INTENT_MAP = {
    "travel": ["旅游", "旅行", "出行", "行程", "攻略", "出差", "自由行", "跟团",
               "旅游规划", "旅游计划", "travel", "trip", "tour"],
    "business_plan": ["商业计划", "创业", "商业方案", "商业规划", "BP", "融资计划",
                      "创业计划", "项目计划", "business plan", "startup"],
    "stock_analysis": ["股票", "黄金", "白银", "基金", "行情", "走势", "量化",
                       "A股", "港股", "美股", "期货", "外汇", "加密货币", "crypto"],
    "study_plan": ["学习计划", "课程", "备考", "复习", "学习路径", "培训",
                   "教育", "考试", "study", "learn"],
    "software_dev": ["开发", "架构", "系统设计", "API", "接口", "数据库设计",
                     "软件", "编程", "代码", "deploy", "开发计划"],
    "data_analysis": ["数据分析", "统计", "报表", "数据可视化", "报表分析",
                      "数据报告", "data analysis"],
    "report": ["报告", "汇报", "总结", "年报", "月报", "周报", "述职"],
    "meeting": ["会议", "讨论", "纪要", "沟通", "评审", "需求评审"],
}


class OutputRouter:
    """输出路由器 — 分析用户需求，自动选择输出格式

    核心逻辑：
    1. 关键词匹配意图
    2. 意图映射成果物组合
    3. 如果没有匹配，根据通用规则生成
    """

    def route(self, user_input: str, intent_type: str = "") -> ArtifactPlan:
        """根据用户输入路由到对应成果物组合

        Args:
            user_input: 用户输入文本
            intent_type: 已识别的意图类型（可选）

        Returns:
            ArtifactPlan 包含推荐生成的成果物列表
        """
        plan = ArtifactPlan()

        # Step 1: 尝试关键词匹配
        matched_intent = self._match_intent(user_input)

        # Step 2: 如果有匹配意图，使用预设映射
        if matched_intent and matched_intent in INTENT_ARTIFACT_MAP:
            mapping = INTENT_ARTIFACT_MAP[matched_intent]
            for artifact_type, category, title, priority in mapping["artifacts"]:
                plan.add(artifact_type, category, title, priority)
            plan.reasoning = mapping["reasoning"]
            logger.info(f"OutputRouter: matched intent '{matched_intent}', "
                        f"planned {len(plan.artifacts)} artifacts")
            return plan

        # Step 3: 通用规则 — 根据输入特征推断
        plan = self._generic_route(user_input, intent_type)
        return plan

    def _match_intent(self, user_input: str) -> Optional[str]:
        """关键词匹配意图"""
        text = user_input.lower()
        best_intent = None
        best_score = 0

        for intent, keywords in KEYWORD_INTENT_MAP.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_intent = intent

        return best_intent if best_score > 0 else None

    def _generic_route(self, user_input: str, intent_type: str = "") -> ArtifactPlan:
        """通用路由规则 — 无精确匹配时的回退策略"""
        plan = ArtifactPlan()
        text = user_input.lower()

        # 通用规则：总是生成 Markdown 作为基础
        plan.add(ArtifactType.MARKDOWN, OutputCategory.DOCUMENT, "回答文档", priority=5)

        # 根据意图类型推断
        if intent_type in ("real_time_data",):
            plan.add(ArtifactType.LINE_CHART, OutputCategory.CHART, "数据趋势图", priority=8)
            plan.add(ArtifactType.EXCEL, OutputCategory.TABLE, "数据表", priority=7)

        # 如果包含比较/对比
        if any(kw in text for kw in ["对比", "比较", "vs", "区别", "优劣"]):
            plan.add(ArtifactType.BAR_CHART, OutputCategory.CHART, "对比图", priority=8)
            plan.add(ArtifactType.MARKDOWN_TABLE, OutputCategory.TABLE, "对比表", priority=7)

        # 如果包含步骤/流程
        if any(kw in text for kw in ["步骤", "流程", "方法", "如何", "怎么做"]):
            plan.add(ArtifactType.FLOWCHART, OutputCategory.DIAGRAM, "流程图", priority=7)
            plan.add(ArtifactType.MARKDOWN, OutputCategory.DOCUMENT, "操作指南", priority=6)

        # 如果包含规划/计划
        if any(kw in text for kw in ["规划", "计划", "安排", "排期"]):
            plan.add(ArtifactType.GANTT, OutputCategory.DIAGRAM, "甘特图", priority=8)
            plan.add(ArtifactType.EXCEL, OutputCategory.TABLE, "时间表", priority=7)

        # 如果包含分析
        if any(kw in text for kw in ["分析", "评估", "诊断"]):
            plan.add(ArtifactType.PDF, OutputCategory.DOCUMENT, "分析报告PDF", priority=7)
            plan.add(ArtifactType.MINDMAP, OutputCategory.DIAGRAM, "分析思维导图", priority=6)

        # 如果内容较长，额外生成 PDF
        if len(text) > 50:
            plan.add(ArtifactType.PDF, OutputCategory.DOCUMENT, "完整内容PDF", priority=3)

        # 至少保留1个成果物
        if len(plan.artifacts) <= 1:
            plan.add(ArtifactType.PDF, OutputCategory.DOCUMENT, "内容PDF", priority=6)

        plan.reasoning = "基于通用规则自动推断成果物组合"
        return plan


# 全局单例
output_router = OutputRouter()

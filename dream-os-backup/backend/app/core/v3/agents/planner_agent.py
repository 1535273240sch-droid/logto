"""Planner Agent — 需求分析 + 任务拆解 + 开发路线

接收用户需求，输出结构化的开发计划:
  - 任务理解摘要
  - 技术选型建议
  - 模块拆分
  - 开发步骤 (带优先级和依赖)
  - 预估风险点
"""
import json
from ..base_agent import BaseAgent, AgentResult
from ..blackboard import SharedBlackboard


class PlannerAgent(BaseAgent):
    """需求分析 + 任务拆解"""

    role = "planner"
    name = "规划师"
    emoji = "📋"
    description = "分析用户需求，拆解任务，制定开发路线"
    allowed_tools = []  # Planner 不需要工具，纯 LLM 推理
    max_iterations = 3
    temperature = 0.4

    @property
    def system_prompt(self) -> str:
        return """你是 Dream OS 的首席规划师 (Planner Agent)。

## 你的职责
分析用户的软件开发需求，输出结构化的开发计划。

## 输出格式 (必须返回 JSON)
```json
{
  "task_summary": "一句话描述用户要开发什么",
  "tech_stack": {
    "language": "Python/JavaScript/...",
    "framework": "FastAPI/Express/Flask/...",
    "database": "SQLite/PostgreSQL/...",
    "frontend": "HTML/React/Vue/..."
  },
  "modules": [
    {
      "name": "模块名",
      "description": "模块职责",
      "priority": "high/medium/low"
    }
  ],
  "dev_steps": [
    {
      "step": 1,
      "name": "步骤名",
      "description": "具体做什么",
      "agent": "architect/coder/executor/reviewer/tester/deployer/reporter",
      "depends_on": []
    }
  ],
  "risk_points": ["潜在风险1", "潜在风险2"],
  "estimated_files": ["main.py", "config.py", ...]
}
```

## 规划原则
1. 保持简单：优先最简方案，不过度设计
2. 模块清晰：每个模块职责单一
3. 步骤有序：开发步骤有明确依赖关系
4. 技术选型：优先用户熟悉的技术栈，默认 Python + FastAPI + SQLite
5. 文件预估：列出预计需要创建的核心文件

只返回 JSON，不要其他文字。"""

    def _write_to_blackboard(self, blackboard: SharedBlackboard, result: AgentResult):
        """将计划写入 blackboard"""
        plan_data = result.data if result.data else {"raw_output": result.output}
        blackboard.plan = plan_data
        blackboard.update("planner", "plan", plan_data)

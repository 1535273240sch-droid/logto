"""V3 专业 Agent 集合

8 个专业 Agent 按开发流程顺序协作:
  1. Planner — 需求分析 + 任务拆解
  2. Architect — 系统架构设计
  3. Coder — 代码编写
  4. Executor — 命令执行 + 依赖安装
  5. Reviewer — 代码审查
  6. Tester — 测试执行
  7. Deployer — 部署
  8. Reporter — 文档生成 + 成果交付
"""

from .planner_agent import PlannerAgent
from .architect_agent import ArchitectAgent
from .coder_agent import CoderAgent
from .executor_agent import ExecutorAgent
from .reviewer_agent import ReviewerAgent
from .tester_agent import TesterAgent
from .deployer_agent import DeployerAgent
from .reporter_agent import ReporterAgent

ALL_AGENTS = [
    PlannerAgent,
    ArchitectAgent,
    CoderAgent,
    ExecutorAgent,
    ReviewerAgent,
    TesterAgent,
    DeployerAgent,
    ReporterAgent,
]

__all__ = [
    "PlannerAgent",
    "ArchitectAgent",
    "CoderAgent",
    "ExecutorAgent",
    "ReviewerAgent",
    "TesterAgent",
    "DeployerAgent",
    "ReporterAgent",
    "ALL_AGENTS",
]

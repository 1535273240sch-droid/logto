"""Orchestrator — 多 Agent 编排器 (状态机驱动)

状态流转:
  idle → planning → architecting → coding → executing
    → reviewing → testing → deploying → reporting → completed
                                ↑              ↓
                          (失败自动返回) ←──────┘

自主循环:
  如果 reviewing/testing 发现问题 → 返回 coding 修复 → 重新执行
  直到测试通过或达到最大迭代次数
"""
import json
import logging
import time
from enum import Enum
from typing import AsyncGenerator

from .blackboard import SharedBlackboard
from .workspace import Workspace
from .sse_v2 import SSEv2
from .base_agent import BaseAgent, AgentResult, EventCallback
from .agents import (
    PlannerAgent, ArchitectAgent, CoderAgent, ExecutorAgent,
    ReviewerAgent, TesterAgent, DeployerAgent, ReporterAgent,
)

logger = logging.getLogger("dream-os.v3.orchestrator")


class OrchestratorState(str, Enum):
    IDLE = "idle"
    PLANNING = "planning"
    ARCHITECTING = "architecting"
    CODING = "coding"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    TESTING = "testing"
    DEPLOYING = "deploying"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"


# Agent 执行顺序 (每轮迭代)
AGENT_PIPELINE = [
    (OrchestratorState.PLANNING, PlannerAgent, "分析需求并制定开发计划"),
    (OrchestratorState.ARCHITECTING, ArchitectAgent, "设计系统架构"),
    (OrchestratorState.CODING, CoderAgent, "编写代码并创建项目文件"),
    (OrchestratorState.EXECUTING, ExecutorAgent, "安装依赖并运行项目"),
    (OrchestratorState.REVIEWING, ReviewerAgent, "审查代码质量"),
    (OrchestratorState.TESTING, TesterAgent, "运行测试验证功能"),
    (OrchestratorState.DEPLOYING, DeployerAgent, "部署到测试环境"),
    (OrchestratorState.REPORTING, ReporterAgent, "生成文档和开发报告"),
]

TOTAL_STEPS = len(AGENT_PIPELINE)


class Orchestrator:
    # 可并行执行的 Agent 对（无依赖关系）
    PARALLEL_PAIRS = [
        (["architect", "tester"], "架构设计 + 测试分析（无依赖）"),
        (["reviewer", "executor"], "代码审查 + 构建运行（无依赖）"),
    ]
    """多 Agent 编排器"""

    def __init__(self, tool_manager):
        """
        Args:
            tool_manager: 全局 ToolManager (包含所有已注册工具)
        """
        self.tool_manager = tool_manager
        self.state = OrchestratorState.IDLE
        self.blackboard = SharedBlackboard()
        self.workspace: Workspace | None = None
        self.agents: dict[str, BaseAgent] = {}

        # 初始化所有 Agent
        for state, agent_cls, _ in AGENT_PIPELINE:
            agent = agent_cls()
            agent.setup_tools(tool_manager)
            self.agents[state.value] = agent

    async def run(
        self,
        requirement: str,
        task_id: str,
        emit: EventCallback,
        max_iterations: int = 3,
    ) -> AsyncGenerator[dict, None]:
        """主循环：按状态机顺序调度 Agent

        Args:
            requirement: 用户需求
            task_id: 开发任务 ID
            emit: SSE 事件回调
            max_iterations: 最大自主修复迭代次数

        Yields:
            事件字典
        """
        start_time = time.time()

        # ── 初始化 ──
        self.blackboard.requirement = requirement
        self.blackboard.project_id = task_id
        self.blackboard.max_iterations = max_iterations

        # 初始化工作空间
        self.workspace = Workspace(task_id)
        workspace_path = self.workspace.init()
        self.blackboard.workspace_path = workspace_path

        # 发送 dev_start 事件
        agent_names = [a.name for a in self.agents.values()]
        await emit({
            "type": "dev_start",
            "task_id": task_id,
            "requirement": requirement[:500],
            "workspace": workspace_path,
            "agents": [a.to_info() for a in self.agents.values()],
        })

        completed_steps = 0
        overall_success = True

        # ── 自主循环 ──
        for iteration in range(1, max_iterations + 1):
            self.blackboard.iteration = iteration

            await emit({
                "type": "loop_iteration",
                "iteration": iteration,
                "max_iterations": max_iterations,
                "status": "running",
            })

            # 从 coding 开始的步骤在后续迭代中重新执行
            start_idx = 0 if iteration == 1 else 2  # 跳过 planner 和 architect

            for idx in range(start_idx, len(AGENT_PIPELINE)):
                state, agent_cls, task_desc = AGENT_PIPELINE[idx]
                self.state = state

                agent = self.agents[state.value]

                # 发送 handoff 事件
                if idx > start_idx:
                    prev_agent = AGENT_PIPELINE[idx - 1][1].role
                    await emit({
                        "type": "agent_handoff",
                        "from": prev_agent,
                        "to": agent.role,
                    })

                # 发送进度更新
                percent = (completed_steps / TOTAL_STEPS) * 100
                await emit({
                    "type": "progress_update",
                    "current_agent": agent.role,
                    "completed": completed_steps,
                    "total": TOTAL_STEPS,
                    "percent": percent,
                    "summary": self.blackboard.summary(),
                })

                # 执行 Agent
                result = await agent.run(
                    task=self._build_task(agent, task_desc),
                    blackboard=self.blackboard,
                    emit=emit,
                    workspace_path=workspace_path,
                )

                completed_steps += 1

                # ── 检查是否需要自主修复 ──
                if state == OrchestratorState.TESTING:
                    if not result.success or not self._tests_passed():
                        # 测试失败 → 检查是否还有迭代机会
                        if iteration < max_iterations:
                            await emit({
                                "type": "loop_iteration",
                                "iteration": iteration,
                                "max_iterations": max_iterations,
                                "status": "retrying",
                                "reason": "测试未通过，返回编码阶段修复",
                            })
                            break  # 跳出内循环，进入下一轮迭代
                        else:
                            overall_success = False
                            await emit({
                                "type": "loop_iteration",
                                "iteration": iteration,
                                "max_iterations": max_iterations,
                                "status": "failed",
                                "reason": "达到最大迭代次数，测试仍未通过",
                            })
                elif state == OrchestratorState.REVIEWING:
                    if self._has_critical_issues() and iteration < max_iterations:
                        await emit({
                            "type": "loop_iteration",
                            "iteration": iteration,
                            "max_iterations": max_iterations,
                            "status": "retrying",
                            "reason": "代码审查发现严重问题，返回编码阶段修复",
                        })
                        break
            else:
                # 所有步骤完成 (内循环正常结束)
                break

        # ── 完成 ──
        self.state = OrchestratorState.COMPLETED if overall_success else OrchestratorState.FAILED

        # 保存工作空间状态
        if self.workspace:
            self.workspace.save_state({
                "status": self.state.value,
                "iteration": self.blackboard.iteration,
                "blackboard": self.blackboard.to_dict(),
            })

        # 生成最终摘要
        summary = self._generate_summary()
        duration_ms = (time.time() - start_time) * 1000

        await emit({
            "type": "dev_complete",
            "task_id": task_id,
            "success": overall_success,
            "summary": summary,
            "workspace": workspace_path,
            "duration_ms": duration_ms,
            "total_tool_calls": sum(
                len([l for l in self.blackboard.execution_log if l.get("agent") == a.role])
                for a in self.agents.values()
            ),
            "files_created": len(self.blackboard.files),
            "iterations": self.blackboard.iteration,
        })

        return {
            "success": overall_success,
            "summary": summary,
            "workspace": workspace_path,
            "blackboard": self.blackboard.to_dict(),
            "duration_ms": duration_ms,
        }

    def _build_task(self, agent: BaseAgent, default_desc: str) -> str:
        """为 Agent 构建具体任务描述"""
        task = default_desc

        if agent.role == "planner":
            task = f"分析以下需求并制定开发计划:\n\n{self.blackboard.requirement}"
        elif agent.role == "architect":
            task = "基于开发计划，设计系统架构"
        elif agent.role == "coder":
            task = "根据架构设计创建项目文件并编写代码"
            if self.blackboard.review_issues:
                task += "\n\n注意：修复以下代码审查问题:\n"
                for issue in self.blackboard.review_issues:
                    if issue.get("severity") == "error":
                        task += f"- {issue.get('file')}: {issue.get('message')}\n"
            if self.blackboard.test_results and not self.blackboard.test_results.get("passed", True):
                task += "\n\n修复以下测试失败:\n"
                for failure in self.blackboard.test_results.get("failures", []):
                    task += f"- {failure.get('test')}: {failure.get('error')}\n"
        elif agent.role == "executor":
            task = "安装项目依赖并尝试运行项目"
        elif agent.role == "reviewer":
            task = "审查项目代码，检查语法、逻辑、安全问题"
        elif agent.role == "tester":
            task = "运行测试验证项目功能是否正常"
        elif agent.role == "deployer":
            task = "将项目部署到测试环境并验证可访问性"
        elif agent.role == "reporter":
            task = "生成 README.md 和开发报告"

        return task

    def _tests_passed(self) -> bool:
        """检查测试是否通过"""
        tr = self.blackboard.test_results
        return tr.get("passed", False)

    def _has_critical_issues(self) -> bool:
        """检查是否有严重代码问题"""
        for issue in self.blackboard.review_issues:
            if issue.get("severity") == "error":
                return True
        return False

    def _generate_summary(self) -> str:
        """生成开发摘要"""
        parts = []

        # 基本信息
        parts.append(f"开发任务: {self.blackboard.requirement[:100]}")
        parts.append(f"迭代次数: {self.blackboard.iteration}/{self.blackboard.max_iterations}")

        # 文件统计
        if self.blackboard.files:
            total_lines = sum(f.get("lines", 0) for f in self.blackboard.files.values())
            parts.append(f"创建文件: {len(self.blackboard.files)} 个, 共 {total_lines} 行")

        # 测试结果
        if self.blackboard.test_results:
            tr = self.blackboard.test_results
            if tr.get("passed"):
                parts.append(f"测试: ✓ 通过 ({tr.get('passed_count', 0)}/{tr.get('total', 0)})")
            else:
                parts.append(f"测试: ✗ 未通过 ({tr.get('failed_count', 0)} 个失败)")

        # 部署结果
        if self.blackboard.deployment:
            dep = self.blackboard.deployment
            if dep.get("deployed"):
                parts.append(f"部署: ✓ 已部署到 {dep.get('url', '')}")
            else:
                parts.append("部署: ✗ 部署失败")

        # 代码审查
        if self.blackboard.review_issues:
            errors = sum(1 for i in self.blackboard.review_issues if i.get("severity") == "error")
            warnings = sum(1 for i in self.blackboard.review_issues if i.get("severity") == "warning")
            parts.append(f"代码审查: {errors} 错误, {warnings} 警告")

        return "\n".join(parts)

    def get_workspace_files(self) -> list[dict]:
        """获取工作空间文件列表"""
        if self.workspace:
            return self.workspace.list_files()
        return []

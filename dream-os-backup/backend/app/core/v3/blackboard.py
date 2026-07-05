"""SharedBlackboard — 项目级共享上下文 (Agent 间通信的黑板模式)

所有 Agent 通过 Blackboard 共享信息：
  - Planner 写入 plan
  - Architect 写入 architecture
  - Coder 写入 files
  - Executor 写入 execution_log
  - Reviewer 写入 review_issues
  - Tester 写入 test_results
  - Deployer 写入 deployment
  - Reporter 读取以上所有，生成报告

每个 Agent 可读取其他 Agent 的输出作为自己的上下文。
"""
import json
import time
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime


@dataclass
class SharedBlackboard:
    """Agent 间共享的项目上下文"""

    project_id: str = ""
    workspace_path: str = ""
    requirement: str = ""  # 用户原始需求

    # 各 Agent 的输出 (key → value)
    plan: dict = field(default_factory=dict)           # Planner: 任务拆解 + 开发路线
    architecture: dict = field(default_factory=dict)    # Architect: 系统设计
    files: dict[str, dict] = field(default_factory=dict)  # Coder: {filepath: {content_preview, action, lines}}
    execution_log: list[dict] = field(default_factory=list)  # Executor: 命令执行记录
    review_issues: list[dict] = field(default_factory=list)  # Reviewer: 代码问题列表
    test_results: dict = field(default_factory=dict)    # Tester: 测试结果
    deployment: dict = field(default_factory=dict)      # Deployer: 部署信息
    reports: list[dict] = field(default_factory=list)   # Reporter: 生成的报告

    # 操作历史 (所有 Agent 的操作记录)
    history: list[dict] = field(default_factory=list)

    # 迭代信息
    iteration: int = 0
    max_iterations: int = 5

    def update(self, agent: str, key: str, value: Any):
        """Agent 更新黑板数据"""
        if hasattr(self, key):
            old = getattr(self, key)
            if isinstance(old, dict):
                old.update(value if isinstance(value, dict) else {key: value})
            elif isinstance(old, list):
                if isinstance(value, list):
                    old.extend(value)
                else:
                    old.append(value)
            else:
                setattr(self, key, value)
        self.history.append({
            "agent": agent,
            "key": key,
            "timestamp": datetime.now().isoformat(),
            "preview": str(value)[:200] if value else "",
        })

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def get_context_for(self, agent_role: str) -> str:
        """为指定 Agent 构建上下文摘要"""
        parts = []

        # 所有 Agent 都能看到原始需求
        parts.append(f"【用户需求】\n{self.requirement}")

        # 所有 Agent 都能看到当前迭代信息
        parts.append(f"【迭代信息】第 {self.iteration}/{self.max_iterations} 轮")

        # Planner 的输出 (所有 Agent 都需要)
        if self.plan:
            parts.append(f"【开发计划】\n{json.dumps(self.plan, ensure_ascii=False, indent=2)[:2000]}")

        # Architect 的输出 (Coder/Executor/Reviewer/Tester/Deployer 需要)
        if self.architecture and agent_role != "planner":
            parts.append(f"【系统架构】\n{json.dumps(self.architecture, ensure_ascii=False, indent=2)[:2000]}")

        # Coder 的输出 (Reviewer/Tester/Executor 需要)
        if self.files and agent_role in ("reviewer", "tester", "executor", "deployer"):
            file_list = []
            for path, info in self.files.items():
                action = info.get("action", "unknown")
                preview = info.get("content_preview", "")[:100]
                file_list.append(f"  - {path} [{action}] {preview}")
            parts.append(f"【项目文件】\n" + "\n".join(file_list))

        # Executor 的输出 (Reviewer/Tester/Coder 需要)
        if self.execution_log and agent_role in ("reviewer", "tester", "coder"):
            recent = self.execution_log[-5:]
            log_lines = []
            for log in recent:
                status = "✓" if log.get("success") else "✗"
                log_lines.append(f"  {status} {log.get('command', '')[:80]}")
            parts.append(f"【执行日志】\n" + "\n".join(log_lines))

        # Reviewer 的输出 (Coder 需要 - 用于修复)
        if self.review_issues and agent_role == "coder":
            issues = []
            for issue in self.review_issues:
                issues.append(f"  - {issue.get('file', '')}: {issue.get('message', '')}")
            parts.append(f"【代码审查问题】\n" + "\n".join(issues))

        # Tester 的输出 (Coder 需要 - 用于修复失败的测试)
        if self.test_results and agent_role in ("coder", "reviewer", "reporter"):
            parts.append(f"【测试结果】\n{json.dumps(self.test_results, ensure_ascii=False, indent=2)[:1500]}")

        # Deployment 信息 (Reporter 需要)
        if self.deployment and agent_role == "reporter":
            parts.append(f"【部署信息】\n{json.dumps(self.deployment, ensure_ascii=False, indent=2)[:1000]}")

        return "\n\n".join(parts)

    def to_dict(self) -> dict:
        """序列化为字典 (用于持久化)"""
        return {
            "project_id": self.project_id,
            "workspace_path": self.workspace_path,
            "requirement": self.requirement,
            "plan": self.plan,
            "architecture": self.architecture,
            "files": self.files,
            "execution_log": self.execution_log,
            "review_issues": self.review_issues,
            "test_results": self.test_results,
            "deployment": self.deployment,
            "reports": self.reports,
            "history": self.history,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SharedBlackboard":
        """从字典反序列化"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def summary(self) -> str:
        """生成当前状态的简短摘要"""
        return (
            f"迭代 {self.iteration}/{self.max_iterations} | "
            f"文件 {len(self.files)} | "
            f"执行 {len(self.execution_log)} | "
            f"问题 {len(self.review_issues)} | "
            f"测试 {'通过' if self.test_results.get('passed') else '未通过' if self.test_results else '未运行'}"
        )

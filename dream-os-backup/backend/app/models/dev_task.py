"""DevTask 模型 — V3 自主开发任务

记录每个自主开发任务的完整生命周期:
  需求 → 规划 → 架构 → 编码 → 执行 → 审查 → 测试 → 部署 → 报告 → 完成
"""
from sqlalchemy import Column, String, Text, JSON, DateTime, Integer, ForeignKey, Index
from .base import Base, gen_uuid, utcnow


class DevTask(Base):
    """V3 自主开发任务"""
    __tablename__ = "dev_tasks"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(100), default="default", nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)

    # 用户需求
    requirement = Column(Text, nullable=False)

    # 状态: pending/planning/architecting/coding/executing/reviewing/testing/deploying/reporting/completed/failed
    status = Column(String(50), default="pending", nullable=False, index=True)
    current_agent = Column(String(50), default="")

    # 工作空间
    workspace_path = Column(String(500), default="")

    # Agent 输出 (JSON)
    plan = Column(JSON, default=dict)           # Planner 输出
    architecture = Column(JSON, default=dict)   # Architect 输出
    files = Column(JSON, default=list)          # Coder 创建的文件列表
    test_results = Column(JSON, default=dict)   # Tester 结果
    deployment = Column(JSON, default=dict)     # Deployer 结果
    reports = Column(JSON, default=list)        # Reporter 生成的报告

    # 执行日志
    execution_log = Column(JSON, default=list)  # 所有 Agent 的操作记录
    error_log = Column(Text, default="")

    # 迭代信息
    iteration = Column(Integer, default=0)
    max_iterations = Column(Integer, default=3)

    # 最终结果
    result = Column(Text, default="")
    summary = Column(Text, default="")

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_devtask_user_status", "user_id", "status"),
        Index("idx_devtask_project", "project_id"),
    )

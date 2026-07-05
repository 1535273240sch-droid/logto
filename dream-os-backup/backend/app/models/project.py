"""项目模型 — Project Workspace 核心

每个项目拥有：
- 独立聊天（Conversation 关联）
- 独立记忆（Memory 关联）
- 独立文件（File 关联）
- 独立任务（Task 关联）
- 独立摘要（Project Summary）
- 独立工具记录（Tool Record 关联）
"""
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Index, Table
from datetime import datetime
from .base import Base, gen_uuid, utcnow


# ── 项目-会话 关联表 ──────────────────────────────

project_conversations = Table(
    "project_conversations",
    Base.metadata,
    Column("project_id", String(36), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("conversation_id", String(36), ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime, default=utcnow),
    Index("idx_project_conv", "project_id", "conversation_id"),
)


class Project(Base):
    """项目表"""
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(100), default="default", nullable=False, index=True)
    name = Column(String(255), nullable=False, comment="项目名称")
    description = Column(Text, default="", comment="项目描述")
    status = Column(String(50), default="active", comment="active / archived")
    summary = Column(Text, default="", comment="项目摘要 / 开发状态")
    todo_count = Column(Integer, default=0, comment="待办事项计数")
    key_decisions = Column(Text, default="", comment="关键决策记录")
    next_plan = Column(Text, default="", comment="下一步计划")

    # 最后活跃的会话ID（用于快速恢复）
    active_conversation_id = Column(String(36), nullable=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("idx_project_user_status", "user_id", "status"),
    )


class ProjectFile(Base):
    """项目文件表 — 记录项目关联的文件"""
    __tablename__ = "project_files"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(100), default="default", nullable=False)
    filename = Column(String(500), nullable=False, comment="文件名")
    filepath = Column(String(1000), nullable=False, comment="文件路径")
    file_type = Column(String(50), default="", comment="文件类型: md/pdf/docx/xlsx/img/code/log")
    file_size = Column(Integer, default=0, comment="文件大小(bytes)")
    summary = Column(Text, default="", comment="文件内容摘要")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("idx_pfile_project", "project_id"),
    )


class ProjectToolRecord(Base):
    """项目工具记录表 — 记录项目中的工具调用"""
    __tablename__ = "project_tool_records"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    tool_name = Column(String(100), nullable=False)
    command = Column(Text, default="")
    status = Column(String(50), default="success")
    duration_ms = Column(Integer, default=0)
    result_preview = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)
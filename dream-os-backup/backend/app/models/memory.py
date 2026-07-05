"""记忆模型 — V1.5 智能上下文记忆系统

三层记忆架构：
1. 短期记忆（Short-term Memory）：messages 表中的最近消息
2. 会话摘要（Conversation Summary）：conversations.summary 字段
3. 长期记忆（Long-term Memory）：memories 表中持久化的关键信息
"""
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Index
from .base import Base, gen_uuid, utcnow


class Memory(Base):
    """长期记忆表 — 持久化关键信息"""
    __tablename__ = "memory"

    key = Column(String(255), primary_key=True)
    user_id = Column(String(100), default="default", nullable=False)
    value = Column(Text, nullable=False)
    category = Column(String(100), default="general", index=True)
    importance = Column(Integer, default=5, comment="重要程度 1-10，越高越重要")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("idx_memory_user_category", "user_id", "category"),
        Index("idx_memory_importance", "importance"),
    )


class Conversation(Base):
    """会话表 — 每个对话会话"""
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(100), default="default", nullable=False, index=True)
    title = Column(String(255), default="新对话")
    summary = Column(Text, default="", comment="AI 自动生成的会话摘要")
    summary_token_count = Column(Integer, default=0, comment="摘要的 token 预估数")
    message_count = Column(Integer, default=0, comment="消息总数")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("idx_conversation_user", "user_id", "updated_at"),
    )


class Message(Base):
    """消息表 — 会话中的每条消息（短期记忆载体）"""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    conversation_id = Column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False, comment="user / assistant / system / tool")
    content = Column(Text, nullable=False, default="")
    token_count = Column(Integer, default=0, comment="该消息的 token 预估数")
    created_at = Column(DateTime, default=utcnow, index=True)

    __table_args__ = (
        Index("idx_message_conv_created", "conversation_id", "created_at"),
    )
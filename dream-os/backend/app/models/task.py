"""任务模型"""
from sqlalchemy import Column, String, Text, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, gen_uuid, utcnow


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_input = Column(Text, nullable=False)
    plan = Column(JSON, nullable=True)
    result = Column(Text, nullable=True)
    status = Column(String(50), default="pending")  # pending/running/completed/failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

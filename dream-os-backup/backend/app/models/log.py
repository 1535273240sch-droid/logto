"""日志模型"""
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, gen_uuid, utcnow


class Log(Base):
    __tablename__ = "logs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    task_id = Column(UUID(as_uuid=False), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    step_id = Column(Integer, nullable=False)
    step_name = Column(String(255), nullable=True)
    agent = Column(String(100), nullable=False)
    tool = Column(String(100), nullable=False)
    command = Column(Text, nullable=True)
    duration_ms = Column(Integer, default=0)
    exit_code = Column(Integer, default=-1)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    status = Column(String(20), default="running")  # running/success/failed
    created_at = Column(DateTime, default=utcnow)

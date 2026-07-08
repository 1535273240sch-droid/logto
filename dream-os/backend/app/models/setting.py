"""系统设置模型 — 存数据库，改完即时生效，无需重启"""
from sqlalchemy import Column, String, Text, DateTime
from .base import Base, utcnow


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

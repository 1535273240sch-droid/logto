"""Media 模型 — 图片/视频生成记录"""
from sqlalchemy import Column, String, Text, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, gen_uuid, utcnow


class Media(Base):
    __tablename__ = "media"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    type = Column(String(20), nullable=False)  # image / video
    source = Column(String(20), nullable=False)  # generated / uploaded
    prompt = Column(Text, nullable=True)  # 生成用的提示词
    model = Column(String(50), nullable=True)  # 生成用的模型
    url = Column(Text, nullable=False)  # 图片/视频URL
    local_path = Column(Text, nullable=True)  # 本地存储路径
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utcnow)

"""Memory Models - 数据库模型"""
import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from ..db.session import Base


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(100), default="default")
    title = Column(String(200), default="")
    summary = Column(Text, default="")
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String, ForeignKey("conversations.id"))
    role = Column(String(20))
    content = Column(Text)
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    conversation = relationship("Conversation", backref="messages")


class Memory(Base):
    __tablename__ = "memories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100))
    key = Column(String(200))
    value = Column(Text)
    category = Column(String(50), default="auto_extracted")
    importance = Column(Integer, default=5)
    created_at = Column(DateTime, default=datetime.utcnow)

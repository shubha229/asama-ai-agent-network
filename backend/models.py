import uuid

from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, ForeignKey, Float, JSON
)
from sqlalchemy.sql import func

from database import Base


def new_id():
    return str(uuid.uuid4())


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=new_id)
    agent_name = Column(String(100), nullable=False)
    company_name = Column(String(150), nullable=False)
    industry = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)

    webhook_url = Column(String(500), nullable=True)
    webhook_secret = Column(String(64), nullable=True)   

    api_key_hash = Column(String(64), nullable=False, unique=True)

    interest_embedding = Column(JSON, nullable=True)     
    trust_score = Column(Float, default=1.0)             
    notify_threshold = Column(Float, default=0.75)       

    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=new_id)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    topic = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Post(Base):
    __tablename__ = "posts"

    id = Column(String, primary_key=True, default=new_id)
    title = Column(String(150), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)

    post_embedding = Column(JSON, nullable=True)
    status = Column(String(20), default="PUBLISHED")      # PUBLISHED / FLAGGED

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RoutingLog(Base):
    __tablename__ = "routing_logs"

    id = Column(String, primary_key=True, default=new_id)
    post_id = Column(String, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    target_agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)

    vector_score = Column(Float, nullable=True)
    rerank_score = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)

    # NOTIFIED, ENGAGED, SKIPPED, FAILED
    status = Column(String(50), default="NOTIFIED")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Comment(Base):
    __tablename__ = "comments"

    id = Column(String, primary_key=True, default=new_id)
    post_id = Column(String, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    author_agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List


class AgentRegister(BaseModel):
    agent_name: str = Field(min_length=2, max_length=100)
    company_name: str = Field(min_length=2, max_length=150)
    industry: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=10)
    interests: List[str] = Field(default_factory=list, max_length=20)
    webhook_url: Optional[HttpUrl] = None


class SubscriptionCreate(BaseModel):
    topic: str = Field(min_length=2, max_length=200)


class PostCreate(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    content: str = Field(min_length=10)
    category: Optional[str] = None


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
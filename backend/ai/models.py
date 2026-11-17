"""
SQLAlchemy ORM and Pydantic models for GeoHarvest AI V1.
Supports persisted conversations and multi-provider message history.
"""

import datetime
from typing import Any, Dict, List, Literal, Optional
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from backend.ai.config import get_default_gemini_model
from backend.app.dependencies.database import Base

ProviderLiteral = Literal["gemini", "claude", "ollama", "antigravity"]
MessageRoleLiteral = Literal["user", "assistant", "system"]


class AIConversation(Base):
    """Persisted AI chat thread preserving history across provider switches."""

    __tablename__ = "ai_conversations"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False, default="New Conversation")
    provider = Column(String, nullable=False, default="gemini")
    model = Column(String, nullable=False, default=get_default_gemini_model)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    messages = relationship(
        "AIMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AIMessage.id",
    )


class AIMessage(Base):
    """Individual turn inside a conversation, tracking which provider/model generated it."""

    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String, ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False, default="")
    provider = Column(String, nullable=True)
    model = Column(String, nullable=True)
    is_error = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    conversation = relationship("AIConversation", back_populates="messages")


# =============================================================================
# Pydantic Request & Response Schemas
# =============================================================================


class ChatMessageInput(BaseModel):
    role: MessageRoleLiteral
    content: str


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    prompt: Optional[str] = None
    messages: Optional[List[ChatMessageInput]] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    system_instruction: Optional[str] = None


class ProviderConfigRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_model: Optional[str] = None
    vertex_project: Optional[str] = None
    vertex_location: Optional[str] = None
    set_active: bool = True


class ProviderTestRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    vertex_project: Optional[str] = None
    vertex_location: Optional[str] = None


class OllamaPullRequest(BaseModel):
    model: str
    base_url: Optional[str] = None


class ConversationCreateRequest(BaseModel):
    title: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None


class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    provider: Optional[str] = None
    model: Optional[str] = None
    is_error: bool = False
    created_at: str


class ConversationSummary(BaseModel):
    id: str
    title: str
    provider: str
    model: str
    message_count: int
    created_at: str
    updated_at: str


class ConversationDetail(ConversationSummary):
    messages: List[MessageOut] = Field(default_factory=list)


class ChatResponseOut(BaseModel):
    conversation_id: Optional[str] = None
    provider: str
    model: str
    text: str
    finish_reason: str = "stop"
    metadata: Dict[str, Any] = Field(default_factory=dict)

"""SQLAlchemy ORM models mapping to the application data model."""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for SQLAlchemy declarative models."""


class SessionStatus(str, enum.Enum):
    """Lifecycle states for a chat session."""

    ACTIVE = "active"
    ENDED = "ended"
    ERROR = "error"


class MessageSender(str, enum.Enum):
    """Denotes who produced a chat message."""

    USER = "user"
    AGENT = "agent"


class MessageType(str, enum.Enum):
    """Classify the purpose of a chat message."""

    COMMAND = "command"
    RESPONSE = "response"
    CLARIFICATION_REQUEST = "clarification_request"
    CLARIFICATION_RESPONSE = "clarification_response"
    ERROR = "error"
    PROGRESS_UPDATE = "progress_update"


class MessageStatus(str, enum.Enum):
    """Processing status flags for a chat message."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionType(str, enum.Enum):
    """Supported browser action categories."""

    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    EXTRACT = "extract"
    WAIT = "wait"
    BACK = "back"
    FORWARD = "forward"
    REFRESH = "refresh"


class ActionResultStatus(str, enum.Enum):
    """Execution outcome for a browser action."""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class PageState(str, enum.Enum):
    """Track high-level browser context status."""

    IDLE = "idle"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


class ChatSession(Base):
    """Represents a full conversation between user and agent."""

    __tablename__ = "chat_sessions"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=20)
    browser_instance_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False)

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    browser_context: Mapped["BrowserContext | None"] = relationship(
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("timeout_seconds > 0 AND timeout_seconds <= 300", name="ck_chat_sessions_timeout_range"),
    )


class ChatMessage(Base):
    """A single entry in the conversation history."""

    __tablename__ = "chat_messages"

    message_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    sender: Mapped[MessageSender] = mapped_column(Enum(MessageSender), nullable=False)
    message_type: Mapped[MessageType] = mapped_column(Enum(MessageType), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    parent_message_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("chat_messages.message_id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[MessageStatus] = mapped_column(
        Enum(MessageStatus), default=MessageStatus.PENDING, nullable=False
    )

    session: Mapped["ChatSession"] = relationship(back_populates="messages", foreign_keys=[session_id])
    parent_message: Mapped["ChatMessage"] = relationship(remote_side=[message_id], uselist=False)
    actions: Mapped[list["BrowserAction"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    confidence_evaluation: Mapped["ConfidenceEvaluation | None"] = relationship(
        back_populates="message",
        uselist=False,
        cascade="all, delete-orphan",
    )


class BrowserContext(Base):
    """Tracks browser state tied to a chat session."""

    __tablename__ = "browser_contexts"

    context_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_sessions.session_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    current_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_state: Mapped[PageState] = mapped_column(Enum(PageState), default=PageState.IDLE, nullable=False)
    last_page_change_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped["ChatSession"] = relationship(back_populates="browser_context")
    elements: Mapped[list["PageElement"]] = relationship(
        back_populates="context",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PageElement(Base):
    """Cached details about DOM elements in the active page context."""

    __tablename__ = "page_elements"

    element_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    context_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("browser_contexts.context_id", ondelete="CASCADE"),
        nullable=False,
    )
    selector: Mapped[str] = mapped_column(Text, nullable=False)
    element_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    aria_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[float | None] = mapped_column(Float, nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    context: Mapped["BrowserContext"] = relationship(back_populates="elements")


class BrowserAction(Base):
    """A single browser-level operation performed while handling a command."""

    __tablename__ = "browser_actions"

    action_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    message_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_messages.message_id", ondelete="CASCADE"),
        nullable=False,
    )
    action_type: Mapped[ActionType] = mapped_column(Enum(ActionType), nullable=False)
    target: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_status: Mapped[ActionResultStatus] = mapped_column(Enum(ActionResultStatus), nullable=False)
    result_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    message: Mapped["ChatMessage"] = relationship(back_populates="actions")


class ConfidenceEvaluation(Base):
    """Confidence scoring for a parsed chat message."""

    __tablename__ = "confidence_evaluations"

    evaluation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    message_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_messages.message_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    factors: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    clarification_needed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    clarification_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ambiguous_actions: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    evaluation_method: Mapped[str] = mapped_column(String(32), nullable=False, default="hybrid")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    message: Mapped["ChatMessage"] = relationship(back_populates="confidence_evaluation")

    __table_args__ = (
        CheckConstraint("(confidence_score >= 0) AND (confidence_score <= 1)", name="ck_confidence_scores_range"),
    )

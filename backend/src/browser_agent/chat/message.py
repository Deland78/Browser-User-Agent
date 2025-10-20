"""ChatMessage storage service.

Implements:
- ChatMessage model per data-model.md Entity 2
- MessageService for CRUD operations with async SQLite
- Message validation rules

Per tasks.md INFRA-006:
- Message CRUD operations
- SQLite storage using database from SETUP-008
- Support create, get, list by session_id with pagination
- Enforce message validation rules
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from browser_agent.db.init import get_session
from browser_agent.db import models as db_models


class MessageSender(str, Enum):
    """Message sender per data-model.md."""

    USER = "user"
    AGENT = "agent"


class MessageType(str, Enum):
    """Message type per data-model.md."""

    COMMAND = "command"
    RESPONSE = "response"
    CLARIFICATION_REQUEST = "clarification_request"
    CLARIFICATION_RESPONSE = "clarification_response"
    ERROR = "error"
    PROGRESS_UPDATE = "progress_update"


class MessageStatus(str, Enum):
    """Message processing status per data-model.md."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageNotFoundError(Exception):
    """Raised when a message is not found in storage."""

    pass


class MessageValidationError(Exception):
    """Raised when message validation fails."""

    pass


@dataclass
class ChatMessage:
    """A single message in the conversation.

    Per data-model.md Entity 2 (ChatMessage):
    - message_id: Unique identifier
    - session_id: Parent session
    - timestamp: When message was created
    - sender: user or agent
    - message_type: command, response, clarification_request, etc.
    - content: Message text content
    - metadata: Additional data (confidence score, etc.)
    - parent_message_id: For clarification threads
    - status: pending, processing, completed, failed, cancelled

    Validation Rules:
    - content must not be empty for user messages
    - sender=agent requires message_type in [response, clarification_request, error, progress_update]
    - sender=user requires message_type in [command, clarification_response]
    - parent_message_id only valid for message_type=clarification_response
    """

    message_id: str
    session_id: str
    sender: MessageSender
    message_type: MessageType
    content: str
    timestamp: datetime = None
    status: MessageStatus = MessageStatus.PENDING
    metadata: Optional[dict[str, Any]] = None
    parent_message_id: Optional[str] = None

    def __post_init__(self):
        """Validate message fields after initialization."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

        # Validate content is not empty for user messages
        if self.sender == MessageSender.USER and not self.content.strip():
            raise MessageValidationError("User message content must not be empty")

        # Validate message_type for sender
        if self.sender == MessageSender.USER:
            valid_types = [MessageType.COMMAND, MessageType.CLARIFICATION_RESPONSE]
            if self.message_type not in valid_types:
                raise MessageValidationError(
                    f"User messages cannot be of type {self.message_type.value}. "
                    f"Valid types: {[t.value for t in valid_types]}"
                )

        if self.sender == MessageSender.AGENT:
            invalid_types = [MessageType.COMMAND, MessageType.CLARIFICATION_RESPONSE]
            if self.message_type in invalid_types:
                raise MessageValidationError(
                    f"Agent messages cannot be of type {self.message_type.value}"
                )

        # Validate parent_message_id usage
        if self.parent_message_id is not None:
            if self.message_type != MessageType.CLARIFICATION_RESPONSE:
                raise MessageValidationError(
                    "parent_message_id only valid for clarification_response message type"
                )


class MessageService:
    """Async SQLite storage for chat messages.

    Per tasks.md INFRA-006:
    - Create, get, list operations
    - SQLite storage with async support
    - Pagination for message lists
    - Session-based isolation

    Thread-safety: Async-safe via SQLAlchemy async sessions
    Persistence: SQLite database (ephemeral per spec)
    """

    async def create_message(
        self,
        session_id: str,
        sender: MessageSender,
        message_type: MessageType,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
        parent_message_id: Optional[str] = None,
        status: MessageStatus = MessageStatus.PENDING,
    ) -> ChatMessage:
        """Create a new chat message.

        Args:
            session_id: Parent session ID
            sender: USER or AGENT
            message_type: Message classification
            content: Message text
            metadata: Optional additional data
            parent_message_id: Optional parent for clarification threads
            status: Initial status (default: PENDING)

        Returns:
            ChatMessage: Newly created message

        Raises:
            MessageValidationError: If validation fails

        Example:
            >>> service = MessageService()
            >>> message = await service.create_message(
            ...     session_id="session-123",
            ...     sender=MessageSender.USER,
            ...     message_type=MessageType.COMMAND,
            ...     content="Go to google.com"
            ... )
        """
        # Create dataclass for validation
        message_id = str(uuid4())
        message = ChatMessage(
            message_id=message_id,
            session_id=session_id,
            sender=sender,
            message_type=message_type,
            content=content,
            metadata=metadata,
            parent_message_id=parent_message_id,
            status=status,
        )

        # Convert to DB model
        db_message = db_models.ChatMessage(
            message_id=message.message_id,
            session_id=message.session_id,
            timestamp=message.timestamp,
            sender=db_models.MessageSender(message.sender.value),
            message_type=db_models.MessageType(message.message_type.value),
            content=message.content,
            message_metadata=message.metadata,
            parent_message_id=message.parent_message_id,
            status=db_models.MessageStatus(message.status.value),
        )

        # Save to database
        async with get_session() as session:
            session.add(db_message)
            await session.commit()
            await session.refresh(db_message)

        return message

    async def get_message(self, message_id: str) -> ChatMessage:
        """Retrieve message by ID.

        Args:
            message_id: Message identifier

        Returns:
            ChatMessage: Retrieved message

        Raises:
            MessageNotFoundError: If message doesn't exist

        Example:
            >>> message = await service.get_message("msg-123")
        """
        async with get_session() as session:
            result = await session.execute(
                select(db_models.ChatMessage).where(
                    db_models.ChatMessage.message_id == message_id
                )
            )
            db_message = result.scalar_one_or_none()

            if db_message is None:
                raise MessageNotFoundError(f"Message not found: {message_id}")

            return self._db_to_dataclass(db_message)

    async def list_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[ChatMessage]:
        """List messages for a session with pagination.

        Args:
            session_id: Session identifier
            limit: Maximum number of messages to return (None = all)
            offset: Number of messages to skip (for pagination)

        Returns:
            list[ChatMessage]: Messages in chronological order

        Example:
            >>> # Get first 50 messages
            >>> page1 = await service.list_messages("session-123", limit=50, offset=0)
            >>> # Get next 50 messages
            >>> page2 = await service.list_messages("session-123", limit=50, offset=50)
        """
        async with get_session() as session:
            query = (
                select(db_models.ChatMessage)
                .where(db_models.ChatMessage.session_id == session_id)
                .order_by(db_models.ChatMessage.timestamp.asc())
                .offset(offset)
            )

            if limit is not None:
                query = query.limit(limit)

            result = await session.execute(query)
            db_messages = result.scalars().all()

            return [self._db_to_dataclass(msg) for msg in db_messages]

    async def update_message(
        self,
        message_id: str,
        status: Optional[MessageStatus] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ChatMessage:
        """Update message fields.

        Args:
            message_id: Message identifier
            status: New status (optional)
            metadata: New metadata (optional)

        Returns:
            ChatMessage: Updated message

        Raises:
            MessageNotFoundError: If message doesn't exist

        Example:
            >>> updated = await service.update_message(
            ...     "msg-123",
            ...     status=MessageStatus.COMPLETED
            ... )
        """
        async with get_session() as session:
            result = await session.execute(
                select(db_models.ChatMessage).where(
                    db_models.ChatMessage.message_id == message_id
                )
            )
            db_message = result.scalar_one_or_none()

            if db_message is None:
                raise MessageNotFoundError(f"Message not found: {message_id}")

            # Update fields if provided
            if status is not None:
                db_message.status = db_models.MessageStatus(status.value)

            if metadata is not None:
                db_message.message_metadata = metadata

            await session.commit()
            await session.refresh(db_message)

            return self._db_to_dataclass(db_message)

    def _db_to_dataclass(self, db_message: db_models.ChatMessage) -> ChatMessage:
        """Convert database model to dataclass."""
        return ChatMessage(
            message_id=db_message.message_id,
            session_id=db_message.session_id,
            timestamp=db_message.timestamp,
            sender=MessageSender(db_message.sender.value),
            message_type=MessageType(db_message.message_type.value),
            content=db_message.content,
            metadata=db_message.message_metadata,
            parent_message_id=db_message.parent_message_id,
            status=MessageStatus(db_message.status.value),
        )

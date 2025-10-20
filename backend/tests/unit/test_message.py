"""Unit tests for ChatMessage storage service.

Following TDD methodology:
1. RED: Write failing tests
2. GREEN: Implement minimal code to pass
3. REFACTOR: Improve code while keeping tests green

Per tasks.md INFRA-006:
- ChatMessage storage service with CRUD operations
- SQLite storage using database from SETUP-008
- Support create, get, list by session_id with pagination
- Enforce message validation rules from data-model.md

Per data-model.md Entity 2 (ChatMessage):
- message_id, session_id, timestamp, sender, message_type, content, metadata, parent_message_id, status
"""

import pytest
from datetime import datetime
from uuid import uuid4

from browser_agent.chat.message import (
    ChatMessage,
    MessageSender,
    MessageType,
    MessageStatus,
    MessageService,
    MessageNotFoundError,
    MessageValidationError,
)


class TestChatMessage:
    """Test ChatMessage model validation."""

    def test_create_message_with_required_fields(self):
        """Test creating a message with required fields only."""
        message = ChatMessage(
            message_id="msg-123",
            session_id="session-456",
            sender=MessageSender.USER,
            message_type=MessageType.COMMAND,
            content="Go to google.com"
        )

        assert message.message_id == "msg-123"
        assert message.session_id == "session-456"
        assert message.sender == MessageSender.USER
        assert message.message_type == MessageType.COMMAND
        assert message.content == "Go to google.com"
        assert message.status == MessageStatus.PENDING
        assert message.metadata is None
        assert message.parent_message_id is None
        assert isinstance(message.timestamp, datetime)

    def test_create_message_with_metadata(self):
        """Test creating message with metadata."""
        metadata = {"confidence": 0.95, "action_count": 2}
        message = ChatMessage(
            message_id="msg-123",
            session_id="session-456",
            sender=MessageSender.AGENT,
            message_type=MessageType.RESPONSE,
            content="Successfully navigated",
            metadata=metadata
        )

        assert message.metadata == metadata

    def test_sender_validation_for_user_messages(self):
        """Test that user messages must have valid message types."""
        # Valid: user sends command
        message = ChatMessage(
            message_id="msg-1",
            session_id="session-1",
            sender=MessageSender.USER,
            message_type=MessageType.COMMAND,
            content="test"
        )
        assert message.sender == MessageSender.USER

        # Valid: user sends clarification response
        message2 = ChatMessage(
            message_id="msg-2",
            session_id="session-1",
            sender=MessageSender.USER,
            message_type=MessageType.CLARIFICATION_RESPONSE,
            content="test",
            parent_message_id="msg-0"
        )
        assert message2.message_type == MessageType.CLARIFICATION_RESPONSE

        # Invalid: user cannot send response messages
        with pytest.raises(MessageValidationError) as exc_info:
            ChatMessage(
                message_id="msg-3",
                session_id="session-1",
                sender=MessageSender.USER,
                message_type=MessageType.RESPONSE,
                content="test"
            )
        assert "User messages cannot be of type" in str(exc_info.value)

    def test_sender_validation_for_agent_messages(self):
        """Test that agent messages must have valid message types."""
        # Valid: agent sends response
        message = ChatMessage(
            message_id="msg-1",
            session_id="session-1",
            sender=MessageSender.AGENT,
            message_type=MessageType.RESPONSE,
            content="test"
        )
        assert message.sender == MessageSender.AGENT

        # Invalid: agent cannot send command messages
        with pytest.raises(MessageValidationError) as exc_info:
            ChatMessage(
                message_id="msg-2",
                session_id="session-1",
                sender=MessageSender.AGENT,
                message_type=MessageType.COMMAND,
                content="test"
            )
        assert "Agent messages cannot be of type" in str(exc_info.value)

    def test_content_validation(self):
        """Test content cannot be empty for user messages."""
        # Empty content for user message should fail
        with pytest.raises(MessageValidationError) as exc_info:
            ChatMessage(
                message_id="msg-1",
                session_id="session-1",
                sender=MessageSender.USER,
                message_type=MessageType.COMMAND,
                content=""
            )
        assert "content must not be empty" in str(exc_info.value)

    def test_parent_message_validation(self):
        """Test parent_message_id only valid for clarification responses."""
        # Valid: clarification response with parent
        message = ChatMessage(
            message_id="msg-2",
            session_id="session-1",
            sender=MessageSender.USER,
            message_type=MessageType.CLARIFICATION_RESPONSE,
            content="test",
            parent_message_id="msg-1"
        )
        assert message.parent_message_id == "msg-1"

        # Invalid: command with parent_message_id
        with pytest.raises(MessageValidationError) as exc_info:
            ChatMessage(
                message_id="msg-3",
                session_id="session-1",
                sender=MessageSender.USER,
                message_type=MessageType.COMMAND,
                content="test",
                parent_message_id="msg-1"
            )
        assert "parent_message_id only valid for clarification_response" in str(exc_info.value)


@pytest.mark.asyncio
class TestMessageService:
    """Test MessageService CRUD operations with async SQLite."""

    @pytest.fixture
    def service(self):
        """Create a fresh MessageService instance."""
        # Note: Database initialization happens in conftest.py or first use
        return MessageService()

    @pytest.fixture
    def session_id(self):
        """Provide a test session ID."""
        return str(uuid4())

    async def test_create_message(self, service, session_id):
        """Test creating a new message."""
        message = await service.create_message(
            session_id=session_id,
            sender=MessageSender.USER,
            message_type=MessageType.COMMAND,
            content="Go to google.com"
        )

        assert message.message_id is not None
        assert len(message.message_id) == 36  # UUID format
        assert message.session_id == session_id
        assert message.sender == MessageSender.USER
        assert message.message_type == MessageType.COMMAND
        assert message.content == "Go to google.com"
        assert message.status == MessageStatus.PENDING
        assert isinstance(message.timestamp, datetime)

    async def test_create_message_with_metadata(self, service, session_id):
        """Test creating message with metadata."""
        metadata = {"confidence": 0.85, "clarification_reason": "multiple_elements"}

        message = await service.create_message(
            session_id=session_id,
            sender=MessageSender.AGENT,
            message_type=MessageType.CLARIFICATION_REQUEST,
            content="Which button?",
            metadata=metadata
        )

        assert message.metadata == metadata

    async def test_get_message_by_id(self, service, session_id):
        """Test retrieving message by ID."""
        # Create message
        created_message = await service.create_message(
            session_id=session_id,
            sender=MessageSender.USER,
            message_type=MessageType.COMMAND,
            content="test"
        )
        message_id = created_message.message_id

        # Retrieve it
        retrieved_message = await service.get_message(message_id)

        assert retrieved_message.message_id == message_id
        assert retrieved_message.content == "test"

    async def test_get_message_not_found(self, service):
        """Test retrieving non-existent message raises error."""
        with pytest.raises(MessageNotFoundError) as exc_info:
            await service.get_message("non-existent-id")

        assert "Message not found" in str(exc_info.value)

    async def test_list_messages_by_session(self, service, session_id):
        """Test listing all messages for a session."""
        # Create multiple messages
        await service.create_message(
            session_id=session_id,
            sender=MessageSender.USER,
            message_type=MessageType.COMMAND,
            content="First message"
        )
        await service.create_message(
            session_id=session_id,
            sender=MessageSender.AGENT,
            message_type=MessageType.RESPONSE,
            content="Second message"
        )

        # List all for this session
        messages = await service.list_messages(session_id)

        assert len(messages) == 2
        assert messages[0].content == "First message"
        assert messages[1].content == "Second message"

    async def test_list_messages_with_pagination(self, service, session_id):
        """Test pagination when listing messages."""
        # Create 10 messages
        for i in range(10):
            await service.create_message(
                session_id=session_id,
                sender=MessageSender.USER,
                message_type=MessageType.COMMAND,
                content=f"Message {i}"
            )

        # Get first 5
        page1 = await service.list_messages(session_id, limit=5, offset=0)
        assert len(page1) == 5

        # Get next 5
        page2 = await service.list_messages(session_id, limit=5, offset=5)
        assert len(page2) == 5

        # Ensure no overlap
        page1_ids = [m.message_id for m in page1]
        page2_ids = [m.message_id for m in page2]
        assert len(set(page1_ids) & set(page2_ids)) == 0

    async def test_list_messages_empty_session(self, service):
        """Test listing messages for session with no messages."""
        messages = await service.list_messages("empty-session-id")
        assert len(messages) == 0
        assert messages == []

    async def test_update_message_status(self, service, session_id):
        """Test updating message status."""
        # Create message
        message = await service.create_message(
            session_id=session_id,
            sender=MessageSender.USER,
            message_type=MessageType.COMMAND,
            content="test"
        )

        # Update status
        updated = await service.update_message(
            message.message_id,
            status=MessageStatus.COMPLETED
        )

        assert updated.status == MessageStatus.COMPLETED

    async def test_update_message_metadata(self, service, session_id):
        """Test updating message metadata."""
        # Create message without metadata
        message = await service.create_message(
            session_id=session_id,
            sender=MessageSender.USER,
            message_type=MessageType.COMMAND,
            content="test"
        )

        # Add metadata
        new_metadata = {"confidence": 0.92}
        updated = await service.update_message(
            message.message_id,
            metadata=new_metadata
        )

        assert updated.metadata == new_metadata

    async def test_session_isolation(self, service):
        """Test messages are isolated by session."""
        session1 = str(uuid4())
        session2 = str(uuid4())

        # Create messages in different sessions
        await service.create_message(
            session_id=session1,
            sender=MessageSender.USER,
            message_type=MessageType.COMMAND,
            content="Session 1 message"
        )
        await service.create_message(
            session_id=session2,
            sender=MessageSender.USER,
            message_type=MessageType.COMMAND,
            content="Session 2 message"
        )

        # List for each session
        session1_messages = await service.list_messages(session1)
        session2_messages = await service.list_messages(session2)

        assert len(session1_messages) == 1
        assert len(session2_messages) == 1
        assert session1_messages[0].content == "Session 1 message"
        assert session2_messages[0].content == "Session 2 message"

    async def test_chronological_ordering(self, service, session_id):
        """Test messages are returned in chronological order."""
        # Create messages with small delay
        msg1 = await service.create_message(
            session_id=session_id,
            sender=MessageSender.USER,
            message_type=MessageType.COMMAND,
            content="First"
        )
        msg2 = await service.create_message(
            session_id=session_id,
            sender=MessageSender.AGENT,
            message_type=MessageType.RESPONSE,
            content="Second"
        )

        messages = await service.list_messages(session_id)

        assert messages[0].message_id == msg1.message_id
        assert messages[1].message_id == msg2.message_id
        assert messages[0].timestamp <= messages[1].timestamp

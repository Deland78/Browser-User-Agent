"""Unit tests for ChatSession management service.

Following TDD methodology:
1. RED: Write failing tests
2. GREEN: Implement minimal code to pass
3. REFACTOR: Improve code while keeping tests green

Per tasks.md INFRA-005:
- Create ChatSession management service
- In-memory session store (dict)
- Support create, get, update, delete operations
- Track session status (active, ended, error)

Per data-model.md Entity 1 (ChatSession):
- session_id (UUID), created_at, last_activity_at, timeout_seconds, browser_instance_id, status
"""

import pytest
from datetime import datetime, timedelta
from uuid import UUID

from browser_agent.chat.session import (
    ChatSession,
    SessionStatus,
    SessionService,
    SessionNotFoundError,
)


class TestChatSession:
    """Test ChatSession model validation and state transitions."""

    def test_create_session_with_defaults(self):
        """Test creating a session with default values."""
        session = ChatSession(session_id="test-123")

        assert session.session_id == "test-123"
        assert session.status == SessionStatus.ACTIVE
        assert session.timeout_seconds == 20  # Default per FR-020
        assert session.browser_instance_id is None
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.last_activity_at, datetime)
        assert session.last_activity_at == session.created_at

    def test_create_session_with_custom_timeout(self):
        """Test creating session with custom timeout."""
        session = ChatSession(session_id="test-456", timeout_seconds=60)

        assert session.timeout_seconds == 60

    def test_timeout_validation(self):
        """Test timeout_seconds must be > 0 and <= 300."""
        # Valid timeout
        session = ChatSession(session_id="test", timeout_seconds=150)
        assert session.timeout_seconds == 150

        # Invalid: timeout <= 0
        with pytest.raises(ValueError) as exc_info:
            ChatSession(session_id="test", timeout_seconds=0)
        assert "timeout_seconds must be > 0" in str(exc_info.value)

        # Invalid: timeout > 300
        with pytest.raises(ValueError) as exc_info:
            ChatSession(session_id="test", timeout_seconds=301)
        assert "timeout_seconds must be <= 300" in str(exc_info.value)

    def test_last_activity_validation(self):
        """Test last_activity_at >= created_at."""
        now = datetime.now()
        past = now - timedelta(hours=1)

        # Valid: last_activity >= created_at
        session = ChatSession(session_id="test", created_at=past, last_activity_at=now)
        assert session.last_activity_at >= session.created_at

        # Invalid: last_activity < created_at
        with pytest.raises(ValueError) as exc_info:
            ChatSession(session_id="test", created_at=now, last_activity_at=past)
        assert "last_activity_at must be >= created_at" in str(exc_info.value)

    def test_status_transitions(self):
        """Test valid session status transitions."""
        session = ChatSession(session_id="test")

        # Initial status
        assert session.status == SessionStatus.ACTIVE

        # Valid transition: active -> ended
        session.status = SessionStatus.ENDED
        assert session.status == SessionStatus.ENDED

        # Valid transition: active -> error
        session2 = ChatSession(session_id="test2")
        session2.status = SessionStatus.ERROR
        assert session2.status == SessionStatus.ERROR


class TestSessionService:
    """Test SessionService CRUD operations."""

    @pytest.fixture
    def service(self):
        """Create a fresh SessionService instance for each test."""
        return SessionService()

    def test_create_session(self, service):
        """Test creating a new session."""
        session = service.create_session(timeout_seconds=30)

        assert session.session_id is not None
        assert len(session.session_id) == 36  # UUID format
        assert session.status == SessionStatus.ACTIVE
        assert session.timeout_seconds == 30
        assert isinstance(session.created_at, datetime)

    def test_create_session_with_default_timeout(self, service):
        """Test creating session uses default timeout when not specified."""
        session = service.create_session()

        assert session.timeout_seconds == 20  # Default per FR-020

    def test_get_session_by_id(self, service):
        """Test retrieving session by ID."""
        # Create session
        created_session = service.create_session()
        session_id = created_session.session_id

        # Retrieve it
        retrieved_session = service.get_session(session_id)

        assert retrieved_session.session_id == session_id
        assert retrieved_session.status == SessionStatus.ACTIVE

    def test_get_session_not_found(self, service):
        """Test retrieving non-existent session raises error."""
        with pytest.raises(SessionNotFoundError) as exc_info:
            service.get_session("non-existent-id")

        assert "Session not found" in str(exc_info.value)
        assert "non-existent-id" in str(exc_info.value)

    def test_update_session_timeout(self, service):
        """Test updating session timeout."""
        # Create session with default timeout
        session = service.create_session()
        original_id = session.session_id

        # Update timeout
        updated_session = service.update_session(original_id, timeout_seconds=60)

        assert updated_session.session_id == original_id
        assert updated_session.timeout_seconds == 60
        assert updated_session.last_activity_at >= session.last_activity_at

    def test_update_session_browser_instance(self, service):
        """Test updating session browser instance ID."""
        session = service.create_session()

        updated_session = service.update_session(
            session.session_id,
            browser_instance_id="browser-123"
        )

        assert updated_session.browser_instance_id == "browser-123"

    def test_update_session_status(self, service):
        """Test updating session status."""
        session = service.create_session()

        # End the session
        updated_session = service.update_session(
            session.session_id,
            status=SessionStatus.ENDED
        )

        assert updated_session.status == SessionStatus.ENDED

    def test_update_nonexistent_session(self, service):
        """Test updating non-existent session raises error."""
        with pytest.raises(SessionNotFoundError):
            service.update_session("non-existent-id", timeout_seconds=60)

    def test_delete_session(self, service):
        """Test deleting a session."""
        # Create session
        session = service.create_session()
        session_id = session.session_id

        # Delete it
        service.delete_session(session_id)

        # Should not be retrievable
        with pytest.raises(SessionNotFoundError):
            service.get_session(session_id)

    def test_delete_nonexistent_session(self, service):
        """Test deleting non-existent session raises error."""
        with pytest.raises(SessionNotFoundError):
            service.delete_session("non-existent-id")

    def test_list_sessions(self, service):
        """Test listing all sessions."""
        # Create multiple sessions
        session1 = service.create_session()
        session2 = service.create_session()

        # List all
        sessions = service.list_sessions()

        assert len(sessions) == 2
        session_ids = [s.session_id for s in sessions]
        assert session1.session_id in session_ids
        assert session2.session_id in session_ids

    def test_list_sessions_empty(self, service):
        """Test listing sessions when none exist."""
        sessions = service.list_sessions()
        assert len(sessions) == 0
        assert sessions == []

    def test_session_uniqueness(self, service):
        """Test that each session gets a unique ID."""
        session1 = service.create_session()
        session2 = service.create_session()

        assert session1.session_id != session2.session_id

    def test_session_isolation(self, service):
        """Test that sessions are isolated (updating one doesn't affect others)."""
        session1 = service.create_session(timeout_seconds=20)
        session2 = service.create_session(timeout_seconds=30)

        # Update session1
        service.update_session(session1.session_id, timeout_seconds=60)

        # Session2 should be unchanged
        retrieved_session2 = service.get_session(session2.session_id)
        assert retrieved_session2.timeout_seconds == 30

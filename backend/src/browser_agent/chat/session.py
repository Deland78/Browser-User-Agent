"""ChatSession management service.

Implements:
- ChatSession model per data-model.md Entity 1
- SessionService for CRUD operations
- In-memory session store

Per tasks.md INFRA-005:
- Session CRUD operations
- In-memory storage (dict)
- Status tracking (active, ended, error)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4


class SessionStatus(str, Enum):
    """Session status values per data-model.md."""

    ACTIVE = "active"
    ENDED = "ended"
    ERROR = "error"


class SessionNotFoundError(Exception):
    """Raised when a session is not found in the store."""

    pass


@dataclass
class ChatSession:
    """Represents a continuous conversation between user and agent.

    Per data-model.md Entity 1 (ChatSession):
    - session_id: Unique identifier
    - created_at: Session creation timestamp
    - last_activity_at: Last message timestamp
    - timeout_seconds: Page load timeout (default 20s per FR-020)
    - browser_instance_id: Reference to active browser instance (optional)
    - status: Session status (active, ended, error)

    Validation Rules:
    - timeout_seconds must be > 0 and <= 300 (5 minutes max)
    - last_activity_at >= created_at
    - session_id must be unique (enforced by SessionService)

    State Transitions:
    [created] → active → ended
             → active → error
    """

    session_id: str
    timeout_seconds: int = 20  # Default per FR-020
    browser_instance_id: Optional[str] = None
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate session fields after initialization."""
        # Set timestamps if not provided (ensures they're the same initially)
        now = datetime.now()
        if self.created_at is None:
            self.created_at = now
        if self.last_activity_at is None:
            self.last_activity_at = self.created_at

        # Validate timeout_seconds
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")
        if self.timeout_seconds > 300:
            raise ValueError("timeout_seconds must be <= 300 (5 minutes max)")

        # Validate last_activity_at >= created_at
        if self.last_activity_at < self.created_at:
            raise ValueError("last_activity_at must be >= created_at")


# Shared in-memory session store (singleton pattern)
_SESSION_STORE: dict[str, ChatSession] = {}


class SessionService:
    """In-memory session store with CRUD operations.

    Per tasks.md INFRA-005:
    - Create, get, update, delete operations
    - In-memory storage (dict)
    - Track session status

    Thread-safety: Not thread-safe (single-threaded MVP)
    Persistence: Ephemeral (per spec Assumptions - not persisted across restarts)

    Note: Uses shared module-level _SESSION_STORE for persistence across instances
    """

    def __init__(self):
        """Initialize session service with shared store."""
        # Use shared module-level store instead of instance-level
        self._sessions = _SESSION_STORE

    def create_session(
        self, timeout_seconds: int = 20, browser_instance_id: Optional[str] = None
    ) -> ChatSession:
        """Create a new chat session.

        Args:
            timeout_seconds: Page load timeout (default 20s per FR-020)
            browser_instance_id: Optional browser instance reference

        Returns:
            ChatSession: Newly created session

        Example:
            >>> service = SessionService()
            >>> session = service.create_session(timeout_seconds=30)
            >>> assert session.timeout_seconds == 30
        """
        session_id = str(uuid4())
        session = ChatSession(
            session_id=session_id,
            timeout_seconds=timeout_seconds,
            browser_instance_id=browser_instance_id,
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> ChatSession:
        """Retrieve session by ID.

        Args:
            session_id: Session identifier

        Returns:
            ChatSession: Retrieved session

        Raises:
            SessionNotFoundError: If session doesn't exist

        Example:
            >>> session = service.create_session()
            >>> retrieved = service.get_session(session.session_id)
            >>> assert retrieved.session_id == session.session_id
        """
        if session_id not in self._sessions:
            raise SessionNotFoundError(f"Session not found: {session_id}")
        return self._sessions[session_id]

    def update_session(
        self,
        session_id: str,
        timeout_seconds: Optional[int] = None,
        browser_instance_id: Optional[str] = None,
        status: Optional[SessionStatus] = None,
    ) -> ChatSession:
        """Update session fields.

        Args:
            session_id: Session identifier
            timeout_seconds: New timeout value (optional)
            browser_instance_id: New browser instance ID (optional)
            status: New status (optional)

        Returns:
            ChatSession: Updated session

        Raises:
            SessionNotFoundError: If session doesn't exist

        Example:
            >>> session = service.create_session()
            >>> updated = service.update_session(session.session_id, timeout_seconds=60)
            >>> assert updated.timeout_seconds == 60
        """
        session = self.get_session(session_id)

        # Update fields if provided
        if timeout_seconds is not None:
            # Validate before updating
            if timeout_seconds <= 0 or timeout_seconds > 300:
                raise ValueError("timeout_seconds must be > 0 and <= 300")
            session.timeout_seconds = timeout_seconds

        if browser_instance_id is not None:
            session.browser_instance_id = browser_instance_id

        if status is not None:
            session.status = status

        # Update last activity timestamp
        session.last_activity_at = datetime.now()

        return session

    def delete_session(self, session_id: str) -> None:
        """Delete session from store.

        Args:
            session_id: Session identifier

        Raises:
            SessionNotFoundError: If session doesn't exist

        Example:
            >>> session = service.create_session()
            >>> service.delete_session(session.session_id)
            >>> # Session no longer retrievable
        """
        if session_id not in self._sessions:
            raise SessionNotFoundError(f"Session not found: {session_id}")
        del self._sessions[session_id]

    def list_sessions(self) -> list[ChatSession]:
        """List all sessions in the store.

        Returns:
            list[ChatSession]: All sessions (may be empty)

        Example:
            >>> service.create_session()
            >>> service.create_session()
            >>> sessions = service.list_sessions()
            >>> assert len(sessions) == 2
        """
        return list(self._sessions.values())

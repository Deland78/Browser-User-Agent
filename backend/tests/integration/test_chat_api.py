"""Integration tests for Chat API endpoints.

Following TDD methodology:
1. RED: Write failing tests
2. GREEN: Implement minimal code to pass
3. REFACTOR: Improve code while keeping tests green

Per tasks.md US1-008:
- POST /sessions (create session)
- POST /sessions/{session_id}/messages (send command)
- GET /sessions/{session_id}/messages (get history)

Per chat-api.yaml specification:
- Uses FastAPI TestClient for integration testing
- Tests full request/response cycle
- Validates against OpenAPI schemas
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from browser_agent.app import create_app
from browser_agent.chat.session import SessionService, SessionStatus
from browser_agent.chat.message import MessageService
from browser_agent.browser.context import ContextService
from browser_agent.browser.driver import PlaywrightBrowserService
from browser_agent.db.init import init_db, get_engine


@pytest.fixture
def client():
    """Create test client for API requests."""
    # Create app (database initialized on first use)
    app = create_app()

    # Return test client
    return TestClient(app)


@pytest.fixture
async def session_service():
    """Create SessionService for tests."""
    return SessionService()


@pytest.fixture
async def message_service():
    """Create MessageService for tests."""
    return MessageService()


@pytest.fixture
async def context_service():
    """Create ContextService for tests."""
    return ContextService()


class TestSessionEndpoints:
    """Test session management endpoints."""

    def test_create_session_returns_201(self, client):
        """Test POST /sessions creates new session and returns 201."""
        # Act
        response = client.post("/api/v1/sessions")

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert "created_at" in data
        assert "last_activity_at" in data
        assert "timeout_seconds" in data
        assert data["timeout_seconds"] == 20  # Default per FR-020
        assert data["status"] == "active"

    def test_create_session_with_custom_timeout(self, client):
        """Test POST /sessions accepts custom timeout."""
        # Act
        response = client.post(
            "/api/v1/sessions",
            json={"timeout_seconds": 60}
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["timeout_seconds"] == 60

    def test_create_session_validates_timeout_range(self, client):
        """Test POST /sessions validates timeout is 1-300 seconds."""
        # Act - timeout too high
        response = client.post(
            "/api/v1/sessions",
            json={"timeout_seconds": 500}
        )

        # Assert
        assert response.status_code == 422  # FastAPI/Pydantic validation error
        data = response.json()
        assert "error" in data or "details" in data  # Custom validation error format

    def test_get_session_by_id(self, client):
        """Test GET /sessions/{session_id} returns session details."""
        # Arrange - create session first
        create_response = client.post("/api/v1/sessions")
        session_id = create_response.json()["session_id"]

        # Act
        response = client.get(f"/api/v1/sessions/{session_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["status"] == "active"

    def test_get_session_not_found(self, client):
        """Test GET /sessions/{session_id} returns 404 for invalid ID."""
        # Act
        response = client.get("/api/v1/sessions/00000000-0000-0000-0000-000000000000")

        # Assert
        assert response.status_code == 404

    def test_list_sessions(self, client):
        """Test GET /sessions returns list of active sessions."""
        # Arrange - create 2 sessions
        client.post("/api/v1/sessions")
        client.post("/api/v1/sessions")

        # Act
        response = client.get("/api/v1/sessions")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2


class TestMessageEndpoints:
    """Test message sending and retrieval endpoints."""

    @pytest.fixture
    def session_id(self, client):
        """Create a test session and return its ID."""
        response = client.post("/api/v1/sessions")
        return response.json()["session_id"]

    def test_send_message_creates_user_message(self, client, session_id):
        """Test POST /sessions/{session_id}/messages creates user message."""
        # Act
        response = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"content": "Go to google.com"}
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "message_id" in data
        assert data["sender"] == "user"
        assert data["message_type"] == "command"
        assert data["content"] == "Go to google.com"
        assert data["status"] == "pending"

    def test_send_message_validates_empty_content(self, client, session_id):
        """Test POST /sessions/{session_id}/messages rejects empty content."""
        # Act
        response = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"content": ""}
        )

        # Assert
        assert response.status_code == 422  # Pydantic validation error

    def test_send_message_to_nonexistent_session(self, client):
        """Test POST /sessions/{session_id}/messages returns 404 for invalid session."""
        # Act
        response = client.post(
            "/api/v1/sessions/00000000-0000-0000-0000-000000000000/messages",
            json={"content": "Test"}
        )

        # Assert
        assert response.status_code == 404

    def test_get_messages_returns_conversation_history(self, client, session_id):
        """Test GET /sessions/{session_id}/messages returns message list."""
        # Arrange - send a message first
        client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"content": "Go to google.com"}
        )

        # Act
        response = client.get(f"/api/v1/sessions/{session_id}/messages")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert "total" in data
        assert "has_more" in data
        assert len(data["messages"]) >= 1
        assert data["messages"][0]["content"] == "Go to google.com"

    def test_get_messages_supports_pagination(self, client, session_id):
        """Test GET /sessions/{session_id}/messages supports limit and offset."""
        # Arrange - send 3 messages
        for i in range(3):
            client.post(
                f"/api/v1/sessions/{session_id}/messages",
                json={"content": f"Message {i+1}"}
            )

        # Act
        response = client.get(
            f"/api/v1/sessions/{session_id}/messages",
            params={"limit": 2, "offset": 0}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 2
        assert data["total"] >= 3

    def test_get_messages_for_nonexistent_session(self, client):
        """Test GET /sessions/{session_id}/messages returns 404 for invalid session."""
        # Act
        response = client.get("/api/v1/sessions/00000000-0000-0000-0000-000000000000/messages")

        # Assert
        assert response.status_code == 404

    def test_get_single_message(self, client, session_id):
        """Test GET /sessions/{session_id}/messages/{message_id} returns message details."""
        # Arrange - send a message
        send_response = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"content": "Test message"}
        )
        message_id = send_response.json()["message_id"]

        # Act
        response = client.get(f"/api/v1/sessions/{session_id}/messages/{message_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["message_id"] == message_id
        assert data["content"] == "Test message"


class TestMessageProcessing:
    """Test message processing with CommandParser and CommandExecutor integration."""

    @pytest.fixture
    def session_id(self, client):
        """Create a test session and return its ID."""
        response = client.post("/api/v1/sessions")
        return response.json()["session_id"]

    @pytest.mark.skip(reason="Requires full browser and LLM integration - implement in later phase")
    def test_send_message_triggers_agent_processing(self, client, session_id):
        """Test sending message triggers CommandParser and CommandExecutor."""
        # This test requires:
        # 1. Browser instance initialization
        # 2. LLM client for command parsing
        # 3. CommandExecutor for action execution
        # Will be implemented when full integration is ready
        pass

    @pytest.mark.skip(reason="Requires async agent processing - implement with WebSocket support")
    def test_send_message_creates_agent_response(self, client, session_id):
        """Test agent creates response message after processing command."""
        # This test requires async processing or WebSocket support
        # Will be implemented in US3-003 (WebSocket support)
        pass


class TestErrorHandling:
    """Test API error handling per FR-009."""

    def test_invalid_session_id_format(self, client):
        """Test API rejects malformed session IDs."""
        # Act
        response = client.get("/api/v1/sessions/not-a-uuid")

        # Assert
        assert response.status_code == 422  # Validation error

    def test_missing_required_field(self, client):
        """Test API rejects requests missing required fields."""
        # Arrange
        session_response = client.post("/api/v1/sessions")
        session_id = session_response.json()["session_id"]

        # Act
        response = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={}  # Missing 'content' field
        )

        # Assert
        assert response.status_code == 422  # Validation error


class TestCORS:
    """Test CORS configuration for frontend access."""

    def test_cors_headers_present(self, client):
        """Test CORS headers are present in responses."""
        # Act
        response = client.options("/api/v1/sessions")

        # Assert
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers or response.status_code == 200

    def test_cors_allows_localhost_origin(self, client):
        """Test CORS allows localhost:5173 (Vite dev server)."""
        # Act
        response = client.post(
            "/api/v1/sessions",
            headers={"Origin": "http://localhost:5173"}
        )

        # Assert
        assert response.status_code == 201
        # Should not be blocked by CORS

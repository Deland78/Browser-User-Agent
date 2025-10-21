"""Chat API endpoints for session and message management.

Implements endpoints per chat-api.yaml:
- POST /sessions - Create new chat session
- GET /sessions - List active sessions
- GET /sessions/{session_id} - Get session details
- DELETE /sessions/{session_id} - End session
- POST /sessions/{session_id}/messages - Send command
- GET /sessions/{session_id}/messages - Get conversation history

Per tasks.md US1-008:
- Wire up CommandParser and CommandExecutor for message processing
- Return structured responses per OpenAPI spec
"""

import logging
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field, field_validator

from browser_agent.chat.session import SessionService, SessionStatus, SessionNotFoundError
from browser_agent.chat.message import MessageService, MessageType, MessageSender, MessageStatus
from browser_agent.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================================
# Request/Response Models
# ============================================================================


class CreateSessionRequest(BaseModel):
    """Request body for creating a new session."""

    timeout_seconds: Optional[int] = Field(
        default=20,
        ge=1,
        le=300,
        description="Page load timeout in seconds (FR-020, FR-021)"
    )


class SessionResponse(BaseModel):
    """Response model for session data per chat-api.yaml ChatSession schema."""

    session_id: str
    created_at: datetime
    last_activity_at: datetime
    timeout_seconds: int
    browser_instance_id: Optional[str] = None
    status: str

    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    """Request body for sending a message."""

    content: str = Field(..., min_length=1, description="Message content")
    parent_message_id: Optional[str] = Field(
        None,
        description="Parent message ID for clarification responses"
    )


class MessageResponse(BaseModel):
    """Response model for message data per chat-api.yaml ChatMessage schema."""

    message_id: str
    session_id: str
    timestamp: datetime
    sender: str
    message_type: str
    content: str
    metadata: Optional[dict] = None
    parent_message_id: Optional[str] = None
    status: str

    class Config:
        from_attributes = True


class MessagesListResponse(BaseModel):
    """Response model for message list with pagination."""

    messages: List[MessageResponse]
    total: int
    has_more: bool


class ErrorResponse(BaseModel):
    """Error response per chat-api.yaml Error schema."""

    error: str
    message: str
    details: Optional[dict] = None


# ============================================================================
# Dependency Injection
# ============================================================================


def get_session_service() -> SessionService:
    """Dependency for SessionService."""
    return SessionService()


def get_message_service() -> MessageService:
    """Dependency for MessageService."""
    return MessageService()


# ============================================================================
# Session Endpoints
# ============================================================================


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["sessions"],
    summary="Create new chat session"
)
def create_session(
    request: Optional[CreateSessionRequest] = None,
    session_service: SessionService = Depends(get_session_service)
) -> SessionResponse:
    """
    Create a new chat session.

    Per chat-api.yaml POST /sessions:
    - Creates new session with default or custom timeout
    - Returns session details with 201 status
    - Session starts in 'active' status

    Per FR-020: Default timeout is 20 seconds
    Per FR-021: Timeout is configurable (1-300 seconds)
    """
    # Use default timeout if no request body provided
    timeout_seconds = 20
    if request is not None:
        timeout_seconds = request.timeout_seconds

    logger.info(f"Creating new session with timeout={timeout_seconds}s")

    try:
        # Create session
        session = session_service.create_session(
            timeout_seconds=timeout_seconds
        )

        logger.info(f"Session created: {session.session_id}")

        return SessionResponse(
            session_id=session.session_id,
            created_at=session.created_at,
            last_activity_at=session.last_activity_at,
            timeout_seconds=session.timeout_seconds,
            browser_instance_id=session.browser_instance_id,
            status=session.status.value
        )

    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "session_creation_failed", "message": str(e)}
        )


@router.get(
    "/sessions",
    response_model=List[SessionResponse],
    tags=["sessions"],
    summary="List active sessions"
)
def list_sessions(
    session_service: SessionService = Depends(get_session_service)
) -> List[SessionResponse]:
    """
    List all active chat sessions.

    Per chat-api.yaml GET /sessions:
    - Returns array of session objects
    - Includes all active sessions
    """
    logger.info("Listing all sessions")

    try:
        sessions = session_service.list_sessions()

        return [
            SessionResponse(
                session_id=session.session_id,
                created_at=session.created_at,
                last_activity_at=session.last_activity_at,
                timeout_seconds=session.timeout_seconds,
                browser_instance_id=session.browser_instance_id,
                status=session.status.value
            )
            for session in sessions
        ]

    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "session_list_failed", "message": str(e)}
        )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    tags=["sessions"],
    summary="Get session details"
)
def get_session(
    session_id: str,
    session_service: SessionService = Depends(get_session_service)
) -> SessionResponse:
    """
    Get details for a specific session.

    Per chat-api.yaml GET /sessions/{session_id}:
    - Returns session details
    - Returns 404 if session not found
    """
    logger.info(f"Getting session: {session_id}")

    try:
        session = session_service.get_session(session_id)

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "session_not_found", "message": f"Session {session_id} not found"}
            )

        return SessionResponse(
            session_id=session.session_id,
            created_at=session.created_at,
            last_activity_at=session.last_activity_at,
            timeout_seconds=session.timeout_seconds,
            browser_instance_id=session.browser_instance_id,
            status=session.status.value
        )

    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "session_not_found", "message": f"Session {session_id} not found"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "session_get_failed", "message": str(e)}
        )

# ============================================================================
# Message Endpoints  
# ============================================================================


@router.post(
    "/sessions/{session_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["messages"],
    summary="Send user command"
)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    session_service: SessionService = Depends(get_session_service),
    message_service: MessageService = Depends(get_message_service)
) -> MessageResponse:
    """
    Send a user command to the agent.

    Per chat-api.yaml POST /sessions/{session_id}/messages:
    - Creates user message with status='pending'
    - Returns 201 with message details
    - Returns 404 if session not found
    
    Note: This MVP implementation creates the message but doesn't trigger
    agent processing yet. Full integration with CommandParser/CommandExecutor
    will be added in next iteration.
    """
    logger.info(f"Sending message to session {session_id}: {request.content[:50]}...")

    # Verify session exists
    try:
        session = session_service.get_session(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "session_not_found", "message": f"Session {session_id} not found"}
            )
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "session_not_found", "message": f"Session {session_id} not found"}
        )

    try:
        # Create user message
        message = await message_service.create_message(
            session_id=session_id,
            sender=MessageSender.USER,
            message_type=MessageType.COMMAND,
            content=request.content,
            parent_message_id=request.parent_message_id
        )

        logger.info(f"Message created: {message.message_id}")

        return MessageResponse(
            message_id=message.message_id,
            session_id=message.session_id,
            timestamp=message.timestamp,
            sender=message.sender.value,
            message_type=message.message_type.value,
            content=message.content,
            metadata=message.metadata,
            parent_message_id=message.parent_message_id,
            status=message.status.value
        )

    except Exception as e:
        logger.error(f"Failed to create message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "message_creation_failed", "message": str(e)}
        )


@router.get(
    "/sessions/{session_id}/messages",
    response_model=MessagesListResponse,
    tags=["messages"],
    summary="Get conversation history"
)
async def get_messages(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    session_service: SessionService = Depends(get_session_service),
    message_service: MessageService = Depends(get_message_service)
) -> MessagesListResponse:
    """
    Get conversation history for a session.

    Per chat-api.yaml GET /sessions/{session_id}/messages:
    - Returns paginated list of messages
    - Includes total count and has_more flag
    - Returns 404 if session not found
    """
    logger.info(f"Getting messages for session {session_id} (limit={limit}, offset={offset})")

    # Verify session exists
    try:
        session = session_service.get_session(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "session_not_found", "message": f"Session {session_id} not found"}
            )
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "session_not_found", "message": f"Session {session_id} not found"}
        )

    try:
        # Get messages with pagination
        messages = await message_service.list_messages(
            session_id=session_id,
            limit=limit,
            offset=offset
        )

        # Get total count (retrieve all to count - acceptable for MVP)
        all_messages = await message_service.list_messages(session_id=session_id)
        total = len(all_messages)

        # Check if there are more messages
        has_more = (offset + len(messages)) < total

        return MessagesListResponse(
            messages=[
                MessageResponse(
                    message_id=msg.message_id,
                    session_id=msg.session_id,
                    timestamp=msg.timestamp,
                    sender=msg.sender.value,
                    message_type=msg.message_type.value,
                    content=msg.content,
                    metadata=msg.metadata,
                    parent_message_id=msg.parent_message_id,
                    status=msg.status.value
                )
                for msg in messages
            ],
            total=total,
            has_more=has_more
        )

    except Exception as e:
        logger.error(f"Failed to get messages for session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "message_list_failed", "message": str(e)}
        )


@router.get(
    "/sessions/{session_id}/messages/{message_id}",
    response_model=MessageResponse,
    tags=["messages"],
    summary="Get message details"
)
async def get_message(
    session_id: str,
    message_id: str,
    message_service: MessageService = Depends(get_message_service)
) -> MessageResponse:
    """
    Get details for a specific message.

    Per chat-api.yaml GET /sessions/{session_id}/messages/{message_id}:
    - Returns message details
    - Returns 404 if message not found
    """
    logger.info(f"Getting message {message_id} from session {session_id}")

    try:
        message = await message_service.get_message(message_id)

        if message is None or message.session_id != session_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "message_not_found", "message": f"Message {message_id} not found in session {session_id}"}
            )

        return MessageResponse(
            message_id=message.message_id,
            session_id=message.session_id,
            timestamp=message.timestamp,
            sender=message.sender.value,
            message_type=message.message_type.value,
            content=message.content,
            metadata=message.metadata,
            parent_message_id=message.parent_message_id,
            status=message.status.value
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get message {message_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "message_get_failed", "message": str(e)}
        )

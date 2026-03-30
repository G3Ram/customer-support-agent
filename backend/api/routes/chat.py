"""FastAPI routes for chat endpoints.

This module implements:
1. POST /api/chat - Synchronous chat endpoint for testing
2. GET /api/chat/stream - SSE streaming endpoint for production
3. GET /api/health - Health check endpoint
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.agent.orchestrator import (
    ErrorEvent,
    TextEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from backend.agent.session import get_or_create_agent_session
from backend.api.schemas import ChatRequest, ChatResponse, EventSchema, HealthResponse
from backend.mcp_layer.mcp_server import mcp

router = APIRouter(prefix="/api")


def agent_event_to_schema(event) -> EventSchema:
    """Convert an AgentEvent to an EventSchema for API responses.

    Args:
        event: An AgentEvent (TextEvent, ToolCallEvent, ToolResultEvent, or ErrorEvent)

    Returns:
        EventSchema with fields populated based on the event type
    """
    data = {"event_type": event.event_type}

    if hasattr(event, "content"):
        data["content"] = event.content

    if hasattr(event, "tool_name"):
        data["tool_name"] = event.tool_name
        data["tool_input"] = event.tool_input
        data["tool_use_id"] = event.tool_use_id

    if hasattr(event, "result"):
        data["result"] = event.result
        data["is_error"] = event.is_error
        data["tool_use_id"] = event.tool_use_id

    if hasattr(event, "error"):
        data["error"] = event.error

    return EventSchema(**data)


@router.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    """Synchronous chat endpoint for testing.

    Collects all events from the agent session and returns them in a single response.
    Useful for testing but not ideal for production (no streaming feedback).

    Args:
        request: ChatRequest with session_id and message

    Returns:
        ChatResponse with all events collected from the conversation
    """
    session = get_or_create_agent_session(request.session_id)
    events = []

    async for event in session.process_turn(request.message):
        events.append(agent_event_to_schema(event))

    return ChatResponse(session_id=request.session_id, events=events)


@router.get("/chat/stream")
async def chat_stream(session_id: str, message: str):
    """SSE streaming endpoint for real-time chat updates.

    Streams events as they occur, providing immediate feedback to the user.
    This is the recommended endpoint for production use.

    Args:
        session_id: Unique session identifier (query parameter)
        message: User message to the agent (query parameter)

    Returns:
        StreamingResponse with SSE events
    """

    async def event_generator():
        """Generate SSE-formatted events from the agent session."""
        session = get_or_create_agent_session(session_id)

        async for event in session.process_turn(message):
            event_schema = agent_event_to_schema(event)
            yield f"data: {event_schema.model_dump_json()}\n\n"

        # Send completion event
        yield 'data: {"event_type": "done"}\n\n'

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/health")
async def health() -> HealthResponse:
    """Health check endpoint.

    Returns the status of the API and lists all available MCP tools.
    Useful for monitoring and debugging.

    Returns:
        HealthResponse with status and tool list
    """
    tools = [t.name for t in await mcp.list_tools()]
    return HealthResponse(status="ok", tools=tools)

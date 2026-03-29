"""Pydantic v2 models for API request/response.

This module defines the request and response schemas for the FastAPI endpoints.
All schemas use Pydantic v2 for validation and serialization.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request schema for the chat endpoint."""

    session_id: str = Field(description="Unique session identifier")
    message: str = Field(description="User message to the agent")


class EventSchema(BaseModel):
    """Schema for agent events streamed to the client.

    This schema matches the AgentEvent union type from orchestrator.py,
    with all fields optional to accommodate different event types.
    """

    event_type: str
    content: str | None = None  # for TextEvent
    tool_name: str | None = None  # for ToolCallEvent
    tool_input: dict | None = None  # for ToolCallEvent
    tool_use_id: str | None = None  # for ToolCallEvent, ToolResultEvent
    result: dict | None = None  # for ToolResultEvent
    is_error: bool | None = None  # for ToolResultEvent
    error: str | None = None  # for ErrorEvent


class ChatResponse(BaseModel):
    """Response schema for the synchronous chat endpoint."""

    session_id: str
    events: list[EventSchema]


class HealthResponse(BaseModel):
    """Response schema for the health check endpoint."""

    status: str
    tools: list[str]

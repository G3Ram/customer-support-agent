"""Agent orchestrator for customer support conversations.

This module implements the main agent loop that:
1. Manages conversation history
2. Calls Claude API with MCP tool integration
3. Enforces prerequisites and idempotency via middleware
4. Streams events (text, tool calls, tool results, errors) to the caller
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import anthropic

from backend.mcp_layer.middleware.idempotency import get_or_create_idempotency_key
from backend.mcp_layer.middleware.prerequisites import (
    PrerequisiteError,
    check_prerequisites,
    update_session_state,
)
from backend.mcp_layer.mcp_server import mcp
from backend.mcp_layer.session_storage import get_session, update_session
from backend.prompts.system_prompt import build_system_prompt
from backend.types.models import ToolName


# ============================================================================
# Event Types
# ============================================================================


@dataclass
class TextEvent:
    """Text content from the agent."""

    content: str
    event_type: str = "text"


@dataclass
class ToolCallEvent:
    """Agent is calling a tool."""

    tool_name: str
    tool_input: dict
    tool_use_id: str
    event_type: str = "tool_call"


@dataclass
class ToolResultEvent:
    """Result from a tool execution."""

    tool_use_id: str
    result: dict
    is_error: bool
    event_type: str = "tool_result"


@dataclass
class ErrorEvent:
    """Error occurred during agent execution."""

    error: str
    event_type: str = "error"


AgentEvent = TextEvent | ToolCallEvent | ToolResultEvent | ErrorEvent


# ============================================================================
# Orchestrator
# ============================================================================


class Orchestrator:
    """Main agent orchestrator that manages conversation state and tool calls."""

    def __init__(self, session_id: str):
        """Initialize the orchestrator with a session.

        Args:
            session_id: Unique identifier for this conversation session
        """
        self.session_id = session_id
        self.system_prompt = build_system_prompt()
        self.history: list[dict] = []
        self.client = anthropic.Anthropic()
        self.model = "claude-sonnet-4-20250514"

        # Initialize session in session_storage
        session = get_session(session_id)
        update_session(session_id, session)

    async def run(self, user_message: str) -> AsyncIterator[AgentEvent]:
        """Execute an agent turn with the given user message.

        This method:
        1. Adds the user message to conversation history
        2. Calls Claude API with tool schema
        3. Processes response blocks (text and tool calls)
        4. Handles tool execution with prerequisite and idempotency checks
        5. Continues the loop if tools were used
        6. Yields events as they occur

        Args:
            user_message: User's message to process

        Yields:
            AgentEvent instances (TextEvent, ToolCallEvent, ToolResultEvent, ErrorEvent)
        """
        self.history.append({"role": "user", "content": user_message})

        while True:
            tools = await self._get_tools_schema()

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=tools,
                messages=self.history,
            )

            assistant_content = []
            tool_results = []
            has_tool_use = False

            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                    yield TextEvent(content=block.text)

                elif block.type == "tool_use":
                    has_tool_use = True
                    assistant_content.append(
                        {
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        }
                    )
                    yield ToolCallEvent(
                        tool_name=block.name,
                        tool_input=block.input,
                        tool_use_id=block.id,
                    )

                    result, is_error = await self._handle_tool_call(
                        block.name, block.input
                    )

                    yield ToolResultEvent(
                        tool_use_id=block.id, result=result, is_error=is_error
                    )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result),
                            "is_error": is_error,
                        }
                    )

            self.history.append({"role": "assistant", "content": assistant_content})

            if has_tool_use:
                self.history.append({"role": "user", "content": tool_results})
                continue

            break

    async def _handle_tool_call(
        self, tool_name: str, tool_input: dict
    ) -> tuple[dict, bool]:
        """Execute a tool call respecting prerequisites and idempotency.

        This method:
        1. Retrieves current session state
        2. Checks prerequisites (raises PrerequisiteError if not satisfied)
        3. Injects session_id into tool_input
        4. Handles idempotency key generation for process_refund
        5. Calls the tool via MCP
        6. Updates session state on success

        Args:
            tool_name: Name of the tool to call
            tool_input: Input parameters for the tool

        Returns:
            Tuple of (result_dict, is_error). Never raises exceptions.
        """
        try:
            # Get current session state from session_storage
            session = get_session(self.session_id)

            # 1. Check prerequisites
            tool_enum = ToolName[tool_name.upper()]
            check_prerequisites(tool_enum, session)

            # 2. Inject session_id so the tool handler can find session state
            tool_input = dict(tool_input)
            tool_input["session_id"] = self.session_id

            # 3. Handle idempotency for process_refund
            if tool_enum == ToolName.PROCESS_REFUND:
                operation_id = tool_input.get("order_id", "unknown")
                idem_key, session = get_or_create_idempotency_key(
                    operation_id, session
                )
                tool_input["idempotency_key"] = idem_key
                update_session(self.session_id, session)

            # 4. Call the tool via MCP
            result = await self._call_mcp_tool(tool_name, tool_input)

            # 5. Update session state on success
            if isinstance(result, dict) and "error" not in result:
                session = get_session(self.session_id)
                updated = update_session_state(tool_enum, result, session)
                update_session(self.session_id, updated)

            return result, False

        except PrerequisiteError as e:
            return {"error": "prerequisite_violation", "message": str(e)}, True

        except Exception as e:
            return {
                "error": "tool_execution_failed",
                "message": "Unable to complete that action right now.",
            }, True

    async def _call_mcp_tool(self, tool_name: str, tool_input: dict) -> dict:
        """Call a FastMCP tool using the mcp.call_tool() method.

        FastMCP returns results as a list of TextContent objects with .text
        attributes containing JSON strings. This method parses them correctly.

        Args:
            tool_name: Name of the tool to call
            tool_input: Input parameters as a dict

        Returns:
            Tool result as a dict
        """
        import json

        result = await mcp.call_tool(tool_name, tool_input)

        # Handle FastMCP TextContent response format
        if isinstance(result, list):
            if len(result) == 0:
                return {}
            item = result[0]
            # TextContent object with .text attribute containing JSON string
            if hasattr(item, "text"):
                try:
                    return json.loads(item.text)
                except json.JSONDecodeError:
                    return {"raw_response": item.text}
            # Already a dict
            if isinstance(item, dict):
                return item
            return {"raw_response": str(item)}

        if isinstance(result, dict):
            return result

        if isinstance(result, str):
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return {"raw_response": result}

        return {"raw_response": str(result)}

    async def _get_tools_schema(self) -> list[dict]:
        """Build Anthropic-compatible tool schema from FastMCP.

        Retrieves registered tools from the MCP server and converts them
        to the format expected by the Anthropic API.

        Returns:
            List of tool schema dicts with name, description, and input_schema
        """
        tools = []
        for tool in await mcp.list_tools():
            tools.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                }
            )
        return tools

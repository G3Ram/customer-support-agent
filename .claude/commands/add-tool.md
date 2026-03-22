---
description: Scaffold a new MCP tool correctly
---
Scaffold a new MCP tool named: $ARGUMENTS

Steps (in order, do not skip):
1. Add $ARGUMENTS to the ToolName enum in backend/types/models.py
2. Create Pydantic input and output models in backend/types/models.py
3. Create backend/mcp/tools/$ARGUMENTS.py using the mcp-tool-specialist subagent
4. Add a stub handler in backend/backends/ that raises NotImplementedError
5. Register the tool in backend/mcp/server.py
6. Verify: python -c "from backend.mcp.server import mcp; print([t.name for t in mcp.list_tools()])"

Do not implement backend logic — stubs only in this command.
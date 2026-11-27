"""MCP server exposing Outlook inbox + department routing to AI clients."""
from mcp.server.fastmcp import FastMCP
from pydantic import Field
import core

mcp = FastMCP("outlook_router")
RO = {"readOnlyHint": True, "openWorldHint": True}

@mcp.tool(annotations={"readOnlyHint": False, "idempotentHint": True, "openWorldHint": True})
def outlook_sync_inbox(top: int = Field(25, ge=1, le=100, description="Newest N messages to pull")) -> dict:
    """Pull newest Outlook inbox emails and auto-route new ones to departments using rules.json."""
    return core.sync_inbox(top)

@mcp.tool(annotations=RO)
def outlook_list_departments() -> list[str]:
    """List valid department names for routing."""
    return core.departments()

@mcp.tool(annotations=RO)
def outlook_list_emails(
    department: str | None = Field(None, description="Filter, e.g. 'Finance'. Omit for all"),
    limit: int = Field(25, ge=1, le=100), offset: int = Field(0, ge=0)) -> dict:
    """List synced emails (subject, sender, preview, department), newest first. Paginated."""
    return core.list_emails(department, limit, offset)

@mcp.tool(annotations={"readOnlyHint": False, "idempotentHint": True, "openWorldHint": True})
def outlook_route_email(
    email_id: str = Field(description="Email id from outlook_list_emails"),
    department: str = Field(description="Target department from outlook_list_departments")) -> dict:
    """Manually (re)route one email to a department. Also tags it in Outlook as a category."""
    return core.route_email(email_id, department)

@mcp.tool(annotations=RO)
def outlook_discover_folders() -> list[dict]:
    """List Outlook mail folders (name, path, item count) that can be learned as departments."""
    return core.discover_folders()

@mcp.tool(annotations={"readOnlyHint": False, "idempotentHint": True, "openWorldHint": True})
def outlook_learn_rules(max_per_folder: int = Field(150, ge=10, le=500)) -> dict:
    """Auto-detect keywords and sender domains from emails already filed in your Outlook folders.
    Folder names become departments. Applies to emails synced from now on."""
    return core.learn_rules(max_per_folder)

@mcp.tool(annotations=RO)
def outlook_show_rules() -> dict:
    """Show the active routing rules (manual rules.json merged with learned rules)."""
    return core.load_rules()

if __name__ == "__main__":
    import sys
    # stdio for Claude Desktop; `python mcp_server.py http` for remote streamable HTTP
    mcp.run(transport="streamable-http" if "http" in sys.argv else "stdio")

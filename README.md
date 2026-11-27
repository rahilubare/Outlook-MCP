# Outlook -> Website bridge (no Microsoft API, no credentials)
Requires CLASSIC Outlook for Windows (not "new Outlook"), open and signed in.

## Windows PC (reads Outlook, runs MCP + sync)
   Quick start: edit then double-click run-windows.bat (website server: ./run-website.sh)
1. `pip install -r requirements.txt`
2. Set env vars: WEBSITE_URL, INGEST_TOKEN
3. Auto-sync every 60s: `python agent.py`
4. Claude Desktop config (%APPDATA%\Claude\claude_desktop_config.json):
   {"mcpServers":{"outlook_router":{"command":"python","args":["C:\\path\\mcp_server.py"],
    "env":{"WEBSITE_URL":"https://mail.yoursite.com","INGEST_TOKEN":"..."}}}}

## Website server (any host; HTTPS required)
Set INGEST_TOKEN (same), DASHBOARD_PASS. Run: `uvicorn web:app --host 0.0.0.0 --port 8000`
Edit rules.json to change departments/keywords/sender domains.

@echo off
REM Local test: sync agent + dashboard on this PC. Classic Outlook must be open.
set DASHBOARD_USER=admin
set DASHBOARD_PASS=test123
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
pip install -q -r requirements.txt
start "Outlook sync" cmd /k "call .venv\Scripts\activate && python agent.py"
echo Open http://localhost:8001  (login: admin / test123)
uvicorn web:app --host 127.0.0.1 --port 8001

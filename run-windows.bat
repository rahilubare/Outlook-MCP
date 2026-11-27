@echo off
REM Run on the Windows PC with classic Outlook open. Edit the two values below first.
set WEBSITE_URL=https://mail.yoursite.com
set INGEST_TOKEN=change-me-long-random
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
pip install -q -r requirements.txt
python agent.py

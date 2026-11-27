#!/usr/bin/env bash
# Run on the website server. Edit the values below first.
export INGEST_TOKEN=change-me-long-random   # must match the Windows PC
export DASHBOARD_USER=admin
export DASHBOARD_PASS=change-me
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q -r requirements.txt
uvicorn web:app --host 0.0.0.0 --port 8000

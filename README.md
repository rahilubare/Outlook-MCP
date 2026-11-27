# MailRouter - Outlook folders to website (no Microsoft API, no credentials)
Needs CLASSIC Outlook for Windows, open and signed in.
Every Outlook mail folder becomes a department and all its emails appear under it. Emails still in the Inbox are
auto-routed to a folder by rules learned from your filed mail, otherwise they stay under "Inbox".

Local test: run `.\run-local.bat`, open http://localhost:8000 (admin / test123).
Windows PC + remote website: see run-windows.bat and run-website.sh.

Optional env vars: SYNC_PER_FOLDER (200), SYNC_SECONDS (60), LEARN_HOURS (24), MIN_SCORE (2),
EXCLUDE_FOLDERS="Folder A,Folder B", INCLUDE_FOLDERS="Sent Items,Drafts", SESSION_SECRET.
Optional custom_rules.json: {"Crew": {"keywords": ["roster"], "domains": ["agency.com"]}}

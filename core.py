"""Shared logic: Outlook desktop (COM) reader, SQLite store, folder-based routing, website push.
No Microsoft API/credentials: it drives the Outlook app that is already signed in on this PC.

Model: every Outlook mail folder is a department. Emails inside a folder belong to it.
Emails still sitting in the Inbox are routed to a folder-department by rules learned from your filed mail,
or stay under "Inbox" when nothing matches."""
import json, math, os, re, sqlite3
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
import httpx

DB_PATH = os.getenv("DB_PATH", "mail.db")
HERE = Path(__file__).parent
CUSTOM_RULES = Path(os.getenv("CUSTOM_RULES", str(HERE / "custom_rules.json")))  # optional manual extras
LEARNED_FILE = Path(os.getenv("LEARNED_FILE", str(HERE / "learned_rules.json")))
DEFAULT_DEPT = "Inbox"
WEBSITE_URL = os.getenv("WEBSITE_URL", "").rstrip("/")   # e.g. https://mail.yoursite.com
INGEST_TOKEN = os.getenv("INGEST_TOKEN", "")             # shared secret with your website
MIN_SCORE = int(os.getenv("MIN_SCORE", "2"))
MAIL_CLASSES = {43, 46, 53}  # mail, delivery/read reports, meeting requests

STOP = set("""the and for you your with from this that have has are was were will not but our all any can
    please thanks thank regards hello dear fwd new update just get out about into more per via one two""".split())
GENERIC_NAME = {"team", "teams", "dept", "department", "group", "mail", "mails", "emails", "email", "folder",
                "inbox", "misc", "other", "general", "old", "new", "all", "response", "followup", "follow",
                "processed", "done", "pending", "completed", "archive"}
FREE_MAIL = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "live.com", "icloud.com", "aol.com",
             "proton.me", "protonmail.com"}
SYSTEM_FOLDERS = {"sent items", "deleted items", "deleted messages", "drafts", "junk email", "junk e-mail", "outbox",
                  "rss feeds", "conversation history", "sync issues", "local failures", "server failures",
                  "conflicts", "clutter", "trash", "notes", "journal", "search folders", "quick step settings",
                  "suggested contacts", "conversation action settings", "yammer root", "files", "externalcontacts"}
_split = lambda v: {x.strip().lower() for x in os.getenv(v, "").split(",") if x.strip()}
EXTRA_EXCLUDE, INCLUDE = _split("EXCLUDE_FOLDERS"), _split("INCLUDE_FOLDERS")  # INCLUDE_FOLDERS="Sent Items" opts a system folder in

# ---------- Outlook (Windows, classic Outlook only) ----------
@contextmanager
def _mapi():
    import pythoncom, win32com.client  # imported lazily so the website can run on Linux
    pythoncom.CoInitialize()
    try:
        yield win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    finally:
        pythoncom.CoUninitialize()

def _smtp(item) -> str:
    try:
        if getattr(item, "SenderEmailType", "") == "EX":  # Exchange users expose an X500 path, not an address
            u = item.Sender.GetExchangeUser()
            if u: return u.PrimarySmtpAddress
    except Exception:
        pass
    return getattr(item, "SenderEmailAddress", "") or ""

def _read_item(it, folder: str) -> dict:
    return dict(id=it.EntryID, subject=it.Subject or "", sender=_smtp(it),
                sender_name=getattr(it, "SenderName", "") or "", received=it.ReceivedTime.isoformat(),
                preview=" ".join((it.Body or "")[:600].split())[:300], folder=folder)

def _tag_outlook(email_id: str, dept: str):
    with _mapi() as ns:
        item = ns.GetItemFromID(email_id)
        keep = [c.strip() for c in (item.Categories or "").split(",")
                if c.strip() and c.strip() not in departments()]  # keep non-department categories
        item.Categories = ", ".join(keep + [dept])
        item.Save()

# ---------- store ----------
def _db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS emails(
        id TEXT PRIMARY KEY, subject TEXT, sender TEXT, sender_name TEXT, received TEXT, preview TEXT,
        department TEXT, routed_by TEXT, folder TEXT, pushed INTEGER DEFAULT 0)""")
    c.execute("CREATE TABLE IF NOT EXISTS tombstones(id TEXT PRIMARY KEY)")
    cols = {r[1] for r in c.execute("PRAGMA table_info(emails)")}
    if "folder" not in cols:  # database from an older version: start clean, the next sync repopulates it
        c.execute("DROP TABLE emails")
        c.execute("""CREATE TABLE emails(id TEXT PRIMARY KEY, subject TEXT, sender TEXT, sender_name TEXT,
            received TEXT, preview TEXT, department TEXT, routed_by TEXT, folder TEXT, pushed INTEGER DEFAULT 0)""")
        c.commit()
    return c

def upsert(rows: list[dict]) -> int:
    """Insert/update emails. A 'manual' route always wins over automatic ones. Returns count of new rows."""
    with _db() as c:
        before = {r[0] for r in c.execute("SELECT id FROM emails")}
        for r in rows:
            c.execute("""INSERT INTO emails(id,subject,sender,sender_name,received,preview,department,routed_by,folder,pushed)
                VALUES(:id,:subject,:sender,:sender_name,:received,:preview,:department,:routed_by,:folder,0)
                ON CONFLICT(id) DO UPDATE SET subject=excluded.subject, preview=excluded.preview, folder=excluded.folder,
                  department=CASE WHEN emails.routed_by='manual' AND excluded.routed_by!='manual' THEN emails.department ELSE excluded.department END,
                  routed_by=CASE WHEN emails.routed_by='manual' AND excluded.routed_by!='manual' THEN 'manual' ELSE excluded.routed_by END""",
                {"folder": "", "routed_by": "auto", **r})
        return sum(r["id"] not in before for r in rows)

def remove_ids(ids: list[str]):
    with _db() as c: c.executemany("DELETE FROM emails WHERE id=?", [(i,) for i in ids])

def set_department(email_id: str, dept: str):
    if dept not in departments():
        raise ValueError(f"Unknown department '{dept}'. Valid: {departments()}")
    with _db() as c:
        if c.execute("UPDATE emails SET department=?, routed_by='manual', pushed=0 WHERE id=?", (dept, email_id)).rowcount == 0:
            raise ValueError("Email not found. Call sync first or check the id.")

def list_emails(department: str | None = None, limit: int = 50, offset: int = 0, q: str | None = None) -> dict:
    where, args = [], []
    if department: where.append("department = ?"); args.append(department)
    if q:
        where.append("(subject LIKE ? OR sender LIKE ? OR sender_name LIKE ? OR preview LIKE ?)"); args += [f"%{q}%"] * 4
    sql = "SELECT * FROM emails" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY received DESC LIMIT ? OFFSET ?"
    with _db() as c:
        rows = [dict(r) for r in c.execute(sql, args + [limit, offset])]
    return {"count": len(rows), "offset": offset, "emails": rows}

def stats() -> dict:
    with _db() as c:
        counts = {r[0]: r[1] for r in c.execute("SELECT department, COUNT(*) FROM emails GROUP BY department")}
    return {"counts": counts, "total": sum(counts.values()), "departments": departments()}

# ---------- routing rules (learned from your folders; custom_rules.json is optional) ----------
def _words(s: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]{3,}", s.lower()) if w not in STOP]

def _empty(): return {"keywords": [], "domains": [], "learned": [], "strong": []}

def load_rules() -> dict:
    custom = json.loads(CUSTOM_RULES.read_text()) if CUSTOM_RULES.exists() else {}
    learned = json.loads(LEARNED_FILE.read_text()) if LEARNED_FILE.exists() else {}
    rules = {k: {**_empty(), "keywords": v.get("keywords", []), "domains": list(v.get("domains", []))} for k, v in custom.items()}
    lower = {k.lower(): k for k in rules}
    for name, v in learned.items():
        r = rules.setdefault(lower.get(name.lower(), name), _empty())
        for f in ("learned", "strong", "domains"): r[f] = r[f] + v.get(f, [])
    return rules

def departments() -> list[str]:
    names = list(load_rules())
    with _db() as c: names += [r[0] for r in c.execute("SELECT DISTINCT department FROM emails")]
    out = [DEFAULT_DEPT]
    for n in names:
        if n and n not in out: out.append(n)
    return out

def classify(subject: str, preview: str, sender: str, sender_name: str = "", rules: dict | None = None) -> str:
    """Score: custom keyword 2, learned keyword 1, folder-name word 3, sender domain 3. Needs MIN_SCORE."""
    text = f"{subject} {preview} {sender_name}".lower()
    words, domain = set(re.findall(r"[a-z]{3,}", text)), sender.lower().split("@")[-1]
    best, best_score = DEFAULT_DEPT, 0
    for dept, r in (rules or load_rules()).items():
        score = (2 * sum(k.lower() in text for k in r["keywords"]) + sum(t in words for t in r["learned"])
                 + 3 * sum(t in words for t in r["strong"]) + 3 * (domain in {d.lower() for d in r["domains"]}))
        if score > best_score: best, best_score = dept, score
    return best if best_score >= MIN_SCORE else DEFAULT_DEPT

# ---------- folder discovery ----------
def _dept_name(name: str) -> str:
    """'__Data Management' -> 'Data Management'"""
    return re.sub(r"^[\W_]+", "", name).strip() or name.strip()

def _excluded(name: str) -> bool:
    n = re.sub(r"\(this computer only\)", "", _dept_name(name).lower()).strip()
    if "this computer only" in name.lower() or n in EXTRA_EXCLUDE: return True
    return n in SYSTEM_FOLDERS and n not in INCLUDE

def _mail_folders(ns, min_items: int = 0):
    """Every mail folder in the mailbox (Inbox subfolders AND root-level folders), up to 5 levels deep."""
    found = []
    def walk(parent, path, depth):
        for f in parent.Folders:
            try:
                if f.DefaultItemType != 0: continue
                name = f.Name
                if _dept_name(name).lower() == "inbox":  # descend into it; the Inbox itself is handled separately
                    walk(f, f"{path}/{name}", depth); continue
                if _excluded(name): continue
                p = f"{path}/{name}"
                count, has_kids = f.Items.Count, f.Folders.Count > 0
                if count >= max(min_items, 1 if has_kids else 0):  # skip empty container folders
                    found.append(({"name": _dept_name(name), "path": p.strip("/"), "items": count}, f))
                if depth < 4: walk(f, p, depth + 1)
            except Exception:
                continue
    walk(ns.GetDefaultFolder(6).Parent, "", 0)
    dup = Counter(i["name"] for i, _ in found)
    for i, _ in found:  # same name in two places: 'Archive (Inbox)' / 'Archive (Followup-up)'
        if dup[i["name"]] > 1:
            parts = i["path"].split("/")
            i["name"] = f"{i['name']} ({_dept_name(parts[-2]) if len(parts) > 1 else 'root'})"
    return found

def discover_folders(min_items: int = 0) -> list[dict]:
    with _mapi() as ns:
        return [i for i, _ in _mail_folders(ns, min_items)]

def _collect_samples(max_per_folder: int) -> dict:
    samples = {}
    with _mapi() as ns:
        for info, f in _mail_folders(ns):
            items = f.Items; items.Sort("[ReceivedTime]", True); rows = []
            for it in items:
                if len(rows) >= max_per_folder: break
                try:
                    if getattr(it, "Class", 0) not in MAIL_CLASSES: continue
                    addr = getattr(it, "SenderEmailAddress", "") or ""
                    rows.append((it.Subject or "", addr.split("@")[-1].lower() if "@" in addr else ""))
                except Exception:
                    continue
            samples[info["name"]] = {"path": info["path"], "rows": rows}
    return samples

def build_rules(samples: dict) -> dict:
    """Distinctive subject words (TF-IDF style across folders) + dominant sender domains per folder."""
    F = len(samples)
    df = {d: Counter() for d in samples}; dom = {d: Counter() for d in samples}
    for d, s in samples.items():
        for subj, dm in s["rows"]:
            df[d].update(set(_words(subj)))
            if dm and dm not in FREE_MAIL: dom[d][dm] += 1
    spread = Counter(t for d in df for t in df[d])  # number of folders each word appears in
    dom_total = Counter()
    for d in dom: dom_total.update(dom[d])
    out = {}
    for d, s in samples.items():
        n = max(len(s["rows"]), 1); need = 3 if n >= 20 else 2
        scored = sorted(((c / n) * math.log((F + 1) / spread[t]), t) for t, c in df[d].items() if c >= need)[::-1]
        out[d] = {"folder": s["path"], "samples": len(s["rows"]), "strong": sorted(set(_words(d)) - GENERIC_NAME),
                  "learned": [t for _, t in scored[:15]],
                  "domains": [x for x, c in dom[d].items() if c >= 3 and c / dom_total[x] >= 0.7]}
    return out

def learn_rules(max_per_folder: int = 150) -> dict:
    samples = _collect_samples(max_per_folder)
    if not samples:
        return {"message": "No mail folders found besides the Inbox."}
    rules = build_rules(samples)
    tmp = LEARNED_FILE.with_suffix(".tmp"); tmp.write_text(json.dumps(rules, indent=1)); tmp.replace(LEARNED_FILE)
    return rules

# ---------- sync: every folder, not just the Inbox ----------
def _prune(folder: str, seen: set, capped: bool) -> int:
    """Remove rows whose email has left this folder (moved/deleted), only within the window we scanned."""
    with _db() as c:
        floor = None
        if capped and seen:
            floor = c.execute(f"SELECT MIN(received) FROM emails WHERE id IN ({','.join('?' * len(seen))})", list(seen)).fetchone()[0]
        gone = [r["id"] for r in c.execute("SELECT id, received FROM emails WHERE folder=?", (folder,))
                if r["id"] not in seen and (floor is None or r["received"] >= floor)]
        for i in gone:
            c.execute("DELETE FROM emails WHERE id=?", (i,)); c.execute("INSERT OR IGNORE INTO tombstones VALUES (?)", (i,))
    return len(gone)

def _reclassify(rules: dict) -> int:
    """Re-route Inbox emails after the rules changed (manual routes are never touched)."""
    changed = 0
    with _db() as c:
        rows = c.execute("SELECT id,subject,preview,sender,sender_name,department FROM emails WHERE folder='Inbox' AND routed_by='auto'").fetchall()
        for r in rows:
            d = classify(r["subject"], r["preview"], r["sender"], r["sender_name"], rules)
            if d != r["department"]:
                c.execute("UPDATE emails SET department=?, pushed=0 WHERE id=?", (d, r["id"])); changed += 1
    return changed

def sync_inbox(per_folder: int | None = None) -> dict:
    per_folder = min(per_folder or int(os.getenv("SYNC_PER_FOLDER", "200")), 500)
    if not LEARNED_FILE.exists(): learn_rules()
    rules = load_rules()
    with _db() as c: known = {r[0] for r in c.execute("SELECT id FROM emails")}
    new = removed = folders = 0
    with _mapi() as ns:
        targets = [("Inbox", None, ns.GetDefaultFolder(6))] + [(i["path"], i["name"], f) for i, f in _mail_folders(ns)]
        for key, dept, f in targets:
            try:
                items = f.Items; items.Sort("[ReceivedTime]", True)
                seen, rows, n = set(), [], 0
                for it in items:
                    if n >= per_folder: break
                    try:
                        if getattr(it, "Class", 0) not in MAIL_CLASSES: continue
                        n += 1; eid = it.EntryID; seen.add(eid)
                        if eid in known: continue  # already stored: skip the slow field reads
                        r = _read_item(it, key)
                    except Exception:
                        continue
                    r["department"] = dept or classify(r["subject"], r["preview"], r["sender"], r["sender_name"], rules)
                    r["routed_by"] = "folder" if dept else "auto"
                    rows.append(r)
                new += upsert(rows); known.update(r["id"] for r in rows)
                if seen or items.Count == 0: removed += _prune(key, seen, n >= per_folder)
                folders += 1
            except Exception:
                continue
    return {"folders": folders, "new": new, "removed": removed, "rerouted": _reclassify(rules), "website": push_pending()}

# ---------- website bridge ----------
def push_pending(batch: int = 400) -> str:
    """Send new/changed emails and removals to the website. Anything that fails is retried next time."""
    if not WEBSITE_URL: return "skipped (WEBSITE_URL not set)"
    try:
        with _db() as c:
            gone = [r[0] for r in c.execute("SELECT id FROM tombstones")]
            rows = [dict(r) for r in c.execute("SELECT * FROM emails WHERE pushed=0")]
        if not rows and not gone: return "up to date"
        chunks = [rows[i:i + batch] for i in range(0, len(rows), batch)] or [[]]
        for n, ch in enumerate(chunks):
            httpx.post(f"{WEBSITE_URL}/api/ingest", timeout=60, headers={"Authorization": f"Bearer {INGEST_TOKEN}"},
                       json={"emails": ch, "remove": gone if n == 0 else []}).raise_for_status()
            with _db() as c:
                c.executemany("UPDATE emails SET pushed=1 WHERE id=?", [(x["id"],) for x in ch])
                if n == 0: c.executemany("DELETE FROM tombstones WHERE id=?", [(g,) for g in gone])
        return f"pushed {len(rows)}, removed {len(gone)}"
    except Exception as e:
        return f"push failed: {e}"

def route_email(email_id: str, department: str) -> dict:
    set_department(email_id, department)
    res = {"routed": email_id, "department": department, "outlook_tagged": True}
    try: _tag_outlook(email_id, department)
    except Exception as e: res.update(outlook_tagged=False, warning=f"Outlook tag failed: {e}")
    res["website"] = push_pending()
    return res

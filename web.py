"""MailRouter website. Run: uvicorn web:app --host 0.0.0.0 --port 8000  (put HTTPS in front of it)
Pages: /  (public landing)   /login   /app (needs sign-in)   API: /api/*   Bridge push: /api/ingest"""
import base64, hashlib, hmac, os, secrets, time
from collections import defaultdict
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
import core, pages

app = FastAPI(title="MailRouter", docs_url=None, redoc_url=None, openapi_url=None)
SECRET = (os.getenv("SESSION_SECRET") or secrets.token_hex(32)).encode()  # unset = sessions reset on restart
TTL = 8 * 3600
FAILS: dict[str, list[float]] = defaultdict(list)

@app.middleware("http")
async def headers(request: Request, call_next):
    r = await call_next(request)
    r.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer"})
    if request.url.path.startswith(("/api", "/app")): r.headers["Cache-Control"] = "no-store"
    return r

# ---- signed-cookie sessions ----
def _sig(body: str) -> str: return hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest()

def make_session(user: str) -> str:
    body = f"{user}|{int(time.time()) + TTL}"
    return base64.urlsafe_b64encode(body.encode()).decode() + "." + _sig(body)

def read_session(tok: str) -> str | None:
    try:
        b64, sig = tok.rsplit(".", 1)
        body = base64.urlsafe_b64decode(b64.encode()).decode()
        user, exp = body.rsplit("|", 1)
        return user if hmac.compare_digest(sig, _sig(body)) and int(exp) > time.time() else None
    except Exception:
        return None

def api_user(request: Request) -> str:
    u = read_session(request.cookies.get("sid", ""))
    if not u: raise HTTPException(401, "Not signed in")
    return u

class Login(BaseModel):
    username: str
    password: str

@app.post("/api/login")
def login(b: Login, request: Request):
    pw = os.getenv("DASHBOARD_PASS")
    if not pw: raise HTTPException(503, "Server is not configured: set DASHBOARD_PASS.")
    ip, now = (request.client.host if request.client else "?"), time.time()
    FAILS[ip] = [t for t in FAILS[ip] if now - t < 300]
    if len(FAILS[ip]) >= 5: raise HTTPException(429, "Too many attempts. Try again in a few minutes.")
    ok = secrets.compare_digest(b.username.encode(), os.getenv("DASHBOARD_USER", "admin").encode()) \
       & secrets.compare_digest(b.password.encode(), pw.encode())
    if not ok:
        FAILS[ip].append(now); raise HTTPException(401, "Incorrect username or password.")
    resp = JSONResponse({"ok": True})
    secure = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    resp.set_cookie("sid", make_session(b.username), max_age=TTL, httponly=True, samesite="lax", secure=secure)
    return resp

@app.post("/api/logout")
def logout():
    resp = JSONResponse({"ok": True}); resp.delete_cookie("sid"); return resp

# ---- pages ----
@app.get("/", response_class=HTMLResponse)
def home(): return pages.LANDING

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if read_session(request.cookies.get("sid", "")): return RedirectResponse("/app", 303)
    return pages.LOGIN

@app.get("/app", response_class=HTMLResponse)
def dashboard(request: Request):
    if not read_session(request.cookies.get("sid", "")): return RedirectResponse("/login", 303)
    return pages.APP

# ---- data API (signed-in users) ----
class RouteBody(BaseModel):
    email_id: str
    department: str

@app.get("/api/stats", dependencies=[Depends(api_user)])
def stats(): return core.stats()

@app.get("/api/emails", dependencies=[Depends(api_user)])
def emails(department: str | None = None, q: str | None = None, limit: int = 30, offset: int = 0):
    return core.list_emails(department, min(max(limit, 1), 200), max(offset, 0), q)

@app.post("/api/route", dependencies=[Depends(api_user)])
def route(b: RouteBody):  # website-side reroute only; does not touch Outlook
    try: core.set_department(b.email_id, b.department); return {"ok": True}
    except ValueError as e: raise HTTPException(400, str(e))

# ---- bridge push (bearer token only) ----
class Email(BaseModel):
    id: str; subject: str = ""; sender: str = ""; sender_name: str = ""
    received: str = ""; preview: str = ""; department: str = core.DEFAULT_DEPT; routed_by: str = "auto"

class IngestBody(BaseModel):
    emails: list[Email]

@app.post("/api/ingest")
def ingest(b: IngestBody, authorization: str = Header("")):
    tok = os.getenv("INGEST_TOKEN", "")
    if not tok or not hmac.compare_digest(authorization.encode(), f"Bearer {tok}".encode()):
        raise HTTPException(401, "Invalid ingest token")
    return {"new": core.upsert([e.model_dump() for e in b.emails])}

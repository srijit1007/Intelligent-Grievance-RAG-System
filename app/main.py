import logging, threading, time
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel, Field
from . import config as C, db, gmail, llm, rag
from .pii import redact

log = logging.getLogger("grievance")  # never log message text


def auth(x_api_key: str = Header(default="")):
    if C.API_KEY and x_api_key != C.API_KEY:
        raise HTTPException(401, "invalid API key")


def process(text: str, source: str, ref: Optional[str] = None) -> dict:
    clean = redact(text)[:4000]  # PII never reaches the LLM or the DB
    hits = rag.retrieve(clean)
    return db.get(db.add(source, ref, clean, llm.classify(clean, hits), sorted({h[2] for h in hits})))


def poll_gmail():
    while True:
        try:
            for m in gmail.unread():
                if not db.seen(m["id"]):
                    t = process(m["text"], "gmail", m["id"])
                    if C.AUTO_SEND and t["status"] == "new":
                        gmail.reply(m["id"], t["reply"])
                        db.update(t["id"], status="resolved")
                gmail.mark_read(m["id"])
        except Exception as ex:
            log.error("gmail poll failed: %s", type(ex).__name__)
        time.sleep(C.GMAIL_POLL_SECONDS)


@asynccontextmanager
async def lifespan(_):
    db.init()
    log.info("KB chunks indexed: %d", rag.ingest())
    if C.GMAIL_POLL_SECONDS > 0:
        threading.Thread(target=poll_gmail, daemon=True).start()
    yield


app = FastAPI(title="Grievance RAG", lifespan=lifespan)


class In(BaseModel):
    text: str = Field(min_length=3, max_length=20000)
    source: str = "api"
    ref: Optional[str] = None  # e.g. Gmail message id when called from n8n


class Approve(BaseModel):
    reply: Optional[str] = None  # human-edited reply


def _404():
    raise HTTPException(404, "ticket not found")


@app.get("/health")
def health():
    return {"ok": True, "kb_chunks": rag.col().count()}


@app.post("/grievance", dependencies=[Depends(auth)])
def create(g: In):
    return process(g.text, g.source, g.ref)


@app.get("/tickets", dependencies=[Depends(auth)])
def tickets(status: Optional[str] = None, limit: int = 50):
    return db.list_(status, min(limit, 200))


@app.get("/tickets/{tid}", dependencies=[Depends(auth)])
def ticket(tid: int):
    return db.get(tid) or _404()


@app.post("/tickets/{tid}/approve", dependencies=[Depends(auth)])
def approve(tid: int, a: Approve = Approve()):
    t = db.get(tid) or _404()
    if t["status"] == "resolved":
        raise HTTPException(409, "already resolved")
    reply = a.reply or t["reply"]
    if t["source"] == "gmail":
        gmail.reply(t["ref"], reply)
    db.update(tid, status="resolved", reply=reply)
    return db.get(tid)


@app.post("/kb/ingest", dependencies=[Depends(auth)])
def ingest():
    return {"chunks": rag.ingest()}


# Serve the frontend dashboard. Keep this mount AFTER all API routes.
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if _FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=_FRONTEND_DIR), name="static")
    app.mount("/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="dashboard")

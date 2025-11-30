# main.py
from dotenv import load_dotenv
load_dotenv()

from cachetools import TTLCache
import time
import asyncio
import json
import html as _html
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from models import SummarizeRequest, DraftRequest
from services.summarize import summarize
from services.draft import draft
from services import zoho_mail
import os
import httpx
from services.tasks import extract_tasks
from services.events import extract_events
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup

app = FastAPI(title="G-Assistant Backend")

ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REDIRECT_URI = "https://cliqtrix-3aru.onrender.com/oauth/callback"
OAUTH_BASE = "https://accounts.zoho.in/oauth/v2"
summaries_db = TTLCache(maxsize=100, ttl=600)  # store by user_id

# ------- SSE pubsub (in-memory) -------
SUBSCRIBERS = []  # list of asyncio.Queue()

def create_queue() -> asyncio.Queue:
    return asyncio.Queue()

async def broadcast_summary(obj: dict):
    dead = []
    for q in SUBSCRIBERS:
        try:
            q.put_nowait(obj)
        except Exception:
            dead.append(q)
    for q in dead:
        try:
            SUBSCRIBERS.remove(q)
        except ValueError:
            pass

def format_sse(data: str, event: str = None) -> str:
    msg = ""
    if event:
        msg += f"event: {event}\n"
    for line in data.splitlines():
        msg += f"data: {line}\n"
    msg += "\n"
    return msg
# --------------------------------------

def store_summary(user_id: str, summary: dict):
    summaries_db[user_id] = summary

def get_summary(user_id: str):
    return summaries_db.get(user_id)

# ------------- CORS -------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://mail.zoho.in",
        "https://mail.zoho.com",
        "https://mail.zoho.eu",
        "https://mail.zoho.jp",
        "https://mail.zoho.com.cn",
        "https://127.0.0.1:5000",   # zet run origin (Zest)
        "http://127.0.0.1:5000",
        "https://localhost:5000",
        "http://localhost:5000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --------------------------------

@app.get("/oauth/authorize")
def authorize():
    auth_url = (
        f"{OAUTH_BASE}/auth?"
        f"scope=ZohoMail.messages.ALL,ZohoMail.accounts.READ,ZohoMail.folders.READ&"
        f"client_id={ZOHO_CLIENT_ID}&"
        f"response_type=code&"
        f"access_type=offline&"
        f"redirect_uri={REDIRECT_URI}"
    )
    return {"auth_url": auth_url}


@app.get("/oauth/callback")
async def callback(code: str):
    async with httpx.AsyncClient(timeout=30) as client:
        data = {
            "grant_type": "authorization_code",
            "client_id": ZOHO_CLIENT_ID,
            "client_secret": ZOHO_CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "code": code,
        }
        r = await client.post(f"{OAUTH_BASE}/token", data=data)
        tokens = r.json()
        return {"tokens": tokens}


@app.post("/tasks")
async def tasks(request: Request):
    data = await request.json()
    tasks = await extract_tasks(data["body"])
    return {"tasks": tasks}

@app.post("/events")
async def events(request: Request):
    data = await request.json()
    events = await extract_events(data["body"])
    return {"events": events}


@app.post("/summarize")
async def summarize_email(request: Request):
    """
    Receives webhook (or test POST). Expects JSON with at least 'body' or 'html' and optional 'user_id'.
    Stores summary under user_id and broadcasts it to SSE clients.
    """
    try:
        data = await request.json()
        print("📩 Incoming webhook data:", data)
    except Exception:
        print("⚠️ Zoho ping (no JSON).")
        return JSONResponse({"status": "ok"}, status_code=200)

    # Ignore validation pings
    if "status" in data and data.get("status") == "ok":
        print("✅ Validation ping.")
        return JSONResponse({"status": "pong"}, status_code=200)

    # Extract subject and body
    subject = (
        data.get("subject")
        or data.get("Subject")
        or data.get("summary")
        or data.get("subjectText")
        or "No Subject"
    )

    body = (
        data.get("body")
        or data.get("content")
        or data.get("message")
        or data.get("html")
        or data.get("text")
        or ""
    )

    # If Zoho sends HTML, clean & unescape it
    if body and ("<" in body or "&lt;" in body):
        try:
            # unescape entities then strip tags
            body_unescaped = _html.unescape(body)
            soup = BeautifulSoup(body_unescaped, "html.parser")
            body = soup.get_text(separator="\n").strip()
        except Exception as e:
            print("⚠️ HTML parsing/unescape error:", e)

    # Safety check
    if not body.strip():
        print(f"⚠️ Missing or empty body in webhook data: {data}")
        return JSONResponse({"status": "ok"}, status_code=200)

    print(f"✅ Parsed subject: {subject}")
    print(f"✅ Parsed body preview: {body[:200]}...")

    # Call summarizer logic (your existing service)
    res = await summarize(subject, body)
    user_id = data.get("user_id", "anonymous")

    # Clean the summary text from summarizer (unescape + strip HTML)
    raw_summary = res.get("summary", "") if isinstance(res, dict) else str(res)
    clean_summary = _html.unescape(raw_summary).strip()
    if "<" in clean_summary and ">" in clean_summary:
        try:
            clean_summary = BeautifulSoup(clean_summary, "html.parser").get_text(separator="\n").strip()
        except Exception:
            pass

    stored = {
        "subject": subject,
        "summary": clean_summary,
        "sentiment": res.get("sentiment", "Neutral") if isinstance(res, dict) else "Neutral",
        "timestamp": time.time()
    }

    # store and broadcast
    store_summary(user_id, stored)

    try:
        await broadcast_summary({"user_id": user_id, "data": stored})
    except Exception as e:
        print("⚠️ broadcast error:", e)

    print(f"✅ Summary stored in memory for user {user_id}")

    return JSONResponse({
        "status": "success",
        "summary": clean_summary,
        "sentiment": stored["sentiment"]
    })


@app.get("/summary/{user_id}")
def get_stored_summary(user_id: str):
    summary_data = get_summary(user_id)
    if summary_data:
        return {
            "status": "success",
            "data": summary_data
        }
    else:
        return JSONResponse(
            {"status": "not_found", "message": "No recent summary found"},
            status_code=404
        )

# SSE streaming endpoint
@app.get("/stream")
async def stream_summaries():
    """
    Server-Sent Events endpoint.
    Clients connect with EventSource('/stream') and receive JSON payloads
    whenever broadcast_summary(...) is called.
    """
    q = create_queue()
    SUBSCRIBERS.append(q)

    async def event_generator():
        try:
            # initial connected message
            yield format_sse(json.dumps({"type": "connected", "message": "connected"}))
            while True:
                item = await q.get()
                # item is {"user_id": "...", "data": {...}}
                yield format_sse(json.dumps({"type": "summary", "payload": item}))
        except asyncio.CancelledError:
            return
        finally:
            try:
                SUBSCRIBERS.remove(q)
            except Exception:
                pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/draft-reply")
async def draft_email(request: Request):
    data = await request.json()
    text = await draft(data["body"], data.get("tone", "polite"))
    return {"reply_text": text}

@app.get("/inbox")
async def inbox(request: Request):
    access_token = request.headers.get("x-zoho-oauthtoken")
    refresh_token = request.headers.get("x-zoho-refresh")
    emails = await zoho_mail.get_inbox(access_token, refresh_token)
    return {"emails": emails}


@app.get("/")
def root():
    return {"status": "running", "app": "G-Assistant Backend"}

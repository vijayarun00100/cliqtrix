from dotenv import load_dotenv
load_dotenv()   # <-- Must be first!

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from models import SummarizeRequest, DraftRequest
from services.summarize import summarize
from services.draft import draft
from services import zoho_mail
import os, json
import httpx
from services.tasks import extract_tasks
from services.events import extract_events
app = FastAPI(title="G-Assistant Backend")

ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REDIRECT_URI = "https://cliqtrix-3aru.onrender.com/oauth/callback"
OAUTH_BASE = "https://accounts.zoho.in/oauth/v2"

@app.get("/oauth/authorize")
def authorize():
    auth_url = (
        f"{OAUTH_BASE}/auth?"
        f"scope=ZohoMail.messages.ALL,ZohoMail.accounts.READ&"
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
    data = await request.json()
    res = await summarize(data["subject"], data["body"])
    return JSONResponse(res)

@app.post("/draft-reply")
async def draft_email(request: Request):
    data = await request.json()
    text = await draft(data["body"], data.get("tone", "polite"))
    return {"reply_text": text}

@app.get("/inbox")
async def inbox(request: Request):
    token = request.headers.get("x-zoho-oauthtoken")
    emails = await zoho_mail.get_inbox(token)
    return {"emails": emails}

@app.get("/")
def root():
    return {"status": "running", "app": "G-Assistant Backend"}

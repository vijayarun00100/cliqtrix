from dotenv import load_dotenv
load_dotenv()   # <-- Must be first!

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from models import SummarizeRequest, DraftRequest
from services.summarize import summarize
from services.draft import draft
from services import zoho_mail
import os, json


from services.tasks import extract_tasks
from services.events import extract_events



app = FastAPI(title="G-Assistant Backend")

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

from dotenv import load_dotenv
load_dotenv()   # <-- Must be first!

from cachetools import TTLCache
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from models import SummarizeRequest, DraftRequest
@@ -19,6 +20,13 @@
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REDIRECT_URI = "https://cliqtrix-3aru.onrender.com/oauth/callback"
OAUTH_BASE = "https://accounts.zoho.in/oauth/v2"
summaries_db = TTLCache(maxsize=100, ttl=600)

def store_summary(user_id: str, summary: dict):
    summaries_db[user_id] = summary

def get_summary(user_id: str):
    return summaries_db.get(user_id)


app.add_middleware(
@@ -129,15 +137,36 @@ async def summarize_email(request: Request):

    # --- Call your summarizer logic ---
    res = await summarize(subject, body)
    user_id = data.get("user_id", "anonymous")
    store_summary(user_id, {
    "subject": subject,
    "summary": res.get("summary", ""),
    "sentiment": res.get("sentiment", "Neutral"),
    "timestamp": time.time()
    })

    print(f"✅ Summary generated for '{subject}':", res)
    print(f"✅ Summary stored in memory for user {user_id}")

    return JSONResponse({
        "status": "success",
        "summary": res.get("summary", ""),
        "sentiment": res.get("sentiment", "Neutral")
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


@app.post("/draft-reply")
async def draft_email(request: Request):

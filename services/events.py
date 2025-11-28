from .llm import complete
import json
import re
from datetime import datetime

SYS = (
    "You are an intelligent email event extractor. "
    "Extract meeting details such as title, date, start time, end time, and location "
    "from the email body. "
    "Return only valid JSON in this format: "
    "[{\"title\": \"string\", \"start\": \"ISO8601 datetime\", \"end\": \"ISO8601 datetime or null\", \"location\": \"string or null\"}]. "
    "If nothing is found, return []. "
    "Example input and output:\n"
    "Input: 'Let's meet on Monday, December 2nd at 3 PM at Zoho Chennai office.'\n"
    "Output: [{\"title\": \"Meeting\", \"start\": \"2025-12-02T15:00:00\", \"end\": null, \"location\": \"Zoho Chennai office\"}]"
)

async def extract_events(body: str):
    prompt = f"Extract meetings or events from this email:\n\n{body}\n\nReturn strictly formatted JSON list only."
    raw = await complete(SYS, prompt)
    
    # Cleanup potential JSON noise
    cleaned = raw.strip()
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    try:
        events = json.loads(cleaned)
        if isinstance(events, list):
            # Normalize event timestamps if missing timezone or seconds
            for ev in events:
                if "start" in ev and isinstance(ev["start"], str):
                    try:
                        datetime.fromisoformat(ev["start"].replace("Z", ""))
                    except ValueError:
                        ev["start"] = None
            return events
        else:
            return []
    except Exception:
        return []

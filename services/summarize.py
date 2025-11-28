from .llm import complete
import re

SYS = (
    "You are an AI email summarizer. "
    "Given a subject and body, return a short summary (<=100 words), "
    "a bullet list of action items with optional due dates, "
    "and the overall sentiment (positive, neutral, or negative)."
)

async def summarize(subject: str, body: str):
    prompt = f"Subject: {subject}\n\nBody:\n{body}\n\nFormat output as:\nSUMMARY:\n- ...\nACTIONS:\n- ...\nSENTIMENT: ..."
    raw = await complete(SYS, prompt)

    summary, actions, sentiment = "", [], "neutral"
    lines = raw.splitlines()
    mode = None
    for line in lines:
        line = line.strip()
        if line.upper().startswith("SUMMARY"):
            mode = "summary"; continue
        elif line.upper().startswith("ACTIONS"):
            mode = "actions"; continue
        elif line.upper().startswith("SENTIMENT"):
            sentiment = line.split(":",1)[-1].strip(); continue

        if mode == "summary":
            summary += line + " "
        elif mode == "actions" and line.startswith("-"):
            m = re.search(r"\[due:(.*?)\]", line)
            due = m.group(1).strip() if m else None
            text = line.lstrip("- ").split("[due:")[0].strip()
            actions.append({"text": text, "due": due})
    return {"summary": summary.strip(), "actions": actions, "sentiment": sentiment}

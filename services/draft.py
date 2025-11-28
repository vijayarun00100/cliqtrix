from .llm import complete

SYS = (
    "You are an email drafting assistant. "
    "Compose a short, polite, and professional reply to the given email. "
    "Keep it under 150 words."
)

async def draft(original: str, tone: str = "polite"):
    prompt = f"Tone: {tone}\n\nEmail to reply:\n{original}\n\nReply:\n"
    text = await complete(SYS, prompt)
    return text.strip()

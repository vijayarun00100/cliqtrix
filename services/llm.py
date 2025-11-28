import os, httpx

OPENROUTER_KEY = os.getenv("OPEN_ROUTER_KEY")
BASE = os.getenv("OPENROUTER_BASE", "https://openrouter.ai/api/v1")
MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct")
print("USING KEY:", OPENROUTER_KEY[:15], "...")
async def complete(system: str, user: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "HTTP-Referer": "https://zoho-cliqtrix",
        "X-Title": "G-Assistant",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{BASE}/chat/completions", headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()

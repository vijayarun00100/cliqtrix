import os, httpx, json

OPENROUTER_KEY = os.getenv("OPEN_ROUTER_KEY")
BASE = os.getenv("OPENROUTER_BASE", "https://openrouter.ai/api/v1")
MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct")
print("USING KEY:", OPENROUTER_KEY[:15], "...")
async def complete(system: str, user: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "HTTP-Referer": "https://zoho-cliqtrix",
        "X-Title": "G-Assistant",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.7,
        "max_tokens": 512,
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{BASE}/chat/completions", headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
            print("🧠 OpenRouter raw:", json.dumps(data, indent=2)[:500])  # log first 500 chars
            choices = data.get("choices", [])
            if not choices or "message" not in choices[0]:
                print("⚠️ No valid response from LLM.")
                return ""
            return choices[0]["message"]["content"].strip()
    except httpx.HTTPStatusError as e:
        print(f"🚨 OpenRouter HTTP error: {e.response.status_code} → {e.response.text[:200]}")
        return ""
    except Exception as e:
        print("🚨 OpenRouter unexpected error:", e)
        return ""
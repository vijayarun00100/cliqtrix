import httpx

BASE = "https://mail.zoho.com/api"

async def get_inbox(token: str, limit: int = 5):
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    async with httpx.AsyncClient(timeout=30) as client:
        acc = await client.get(f"{BASE}/accounts", headers=headers)
        acc.raise_for_status()
        account_id = acc.json()["data"][0]["accountId"]
        inbox = await client.get(f"{BASE}/accounts/{account_id}/messages/view?folder=Inbox&limit={limit}", headers=headers)
        inbox.raise_for_status()
        data = inbox.json()["data"]
        return [
            {"subject": m.get("subject"), "from": m.get("fromAddress"), "content": m.get("contentSummary")}
            for m in data
        ]

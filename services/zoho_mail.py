import os, httpx

CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
BASE_URL = "https://mail.zoho.in/api"
TOKEN_URL = "https://accounts.zoho.in/oauth/v2/token"


async def refresh_token(refresh_token: str):
    """Use the refresh token to get a new access token"""
    async with httpx.AsyncClient(timeout=30) as client:
        data = {
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refresh_token,
        }
        r = await client.post(TOKEN_URL, data=data)
        r.raise_for_status()
        return r.json()


async def get_inbox(access_token: str, refresh_token: str = None):
    """Fetch inbox emails, and refresh token if needed"""
    async with httpx.AsyncClient(timeout=30) as client:
        headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}

        
        acc = await client.get(f"{BASE_URL}/accounts", headers=headers)
        if acc.status_code == 401 and refresh_token:
            new_tokens = await refresh_token(refresh_token)
            new_access = new_tokens.get("access_token")
            headers = {"Authorization": f"Zoho-oauthtoken {new_access}"}
            acc = await client.get(f"{BASE_URL}/accounts", headers=headers)

        acc.raise_for_status()
        account_id = acc.json()["data"][0]["accountId"]

        inbox = await client.get(f"{BASE_URL}/accounts/{account_id}/messages/view", headers=headers)
        inbox.raise_for_status()
        msgs = inbox.json().get("data", [])

        emails = []
        for m in msgs[:5]: 
            emails.append({
                "subject": m.get("subject"),
                "from": m.get("fromAddress"),
                "summary": m.get("contentSummary", ""),
            })

        return emails

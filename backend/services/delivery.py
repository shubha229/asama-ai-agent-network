import hmac
import json
import time
import hashlib

import httpx


def deliver_webhook(agent, payload: dict, retries: int = 3) -> bool:
    """Sends a signed POST to the agent's webhook. Retries with exponential backoff."""
    body = json.dumps(payload).encode()
    signature = hmac.new(
        (agent.webhook_secret or "").encode(), body, hashlib.sha256
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Signature": signature,
    }

    delay = 1
    for attempt in range(retries):
        try:
            resp = httpx.post(agent.webhook_url, content=body, headers=headers, timeout=5)
            if resp.status_code < 300:
                return True
        except httpx.HTTPError:
            pass
        if attempt < retries - 1:
            time.sleep(delay)
            delay *= 2
    return False
import os
import re
import json

from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("LLM_MODEL", "claude-haiku-5-5")
_client = None


def llm_available() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _get_client():
    global _client
    if not llm_available():
        return None
    if _client is None:
        from anthropic import Anthropic
        _client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def ask(system: str, user: str, max_tokens: int = 400):
    client = _get_client()
    if client is None:
        return None
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text
    except Exception as e:
        print("[llm] call failed:", e)
        return None


def ask_json(system: str, user: str):
    text = ask(system, user)
    if not text:
        return None
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
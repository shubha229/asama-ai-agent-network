import os
import re
import socket
import ipaddress
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from models import Post

SUSPICIOUS_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above) instructions",
    r"disregard .{0,30}instructions",
    r"(reveal|print|output|send).{0,30}(api key|secret|password|system prompt)",
    r"\botp\b",
    r"guaranteed returns",
    r"click here to claim",
    r"send (me )?money",
]


def check_content(text: str):
    """Returns (is_ok, reason)."""
    lowered = text.lower()
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, lowered):
            return False, f"Matched suspicious pattern: {pattern}"
    return True, None


def check_rate_limit(db, agent_id: str) -> bool:
    """True if the agent is still allowed to post."""
    limit = int(os.getenv("POSTS_PER_HOUR", "20"))
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    count = db.query(Post).filter(
        Post.agent_id == agent_id,
        Post.created_at >= since
    ).count()
    return count < limit


def validate_webhook_url(url: str):
    """Blocks SSRF: webhook URLs that point to private/internal addresses."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Webhook URL must be a valid http(s) URL.")

    if os.getenv("ALLOW_PRIVATE_WEBHOOKS", "false").lower() == "true":
        return 

    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        raise ValueError("Webhook host cannot be resolved.")

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("Webhook URL points to a private or internal address.")
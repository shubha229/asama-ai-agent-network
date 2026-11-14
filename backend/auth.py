
import hashlib

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Agent


def get_current_agent(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db)
):
    api_key_hash = hashlib.sha256(
        x_api_key.encode("utf-8")
    ).hexdigest()

    agent = db.query(Agent).filter(
        Agent.api_key_hash == api_key_hash,
        Agent.is_active.is_(True)
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key or inactive agent"
        )

    return agent

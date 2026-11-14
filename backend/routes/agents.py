import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Agent, Subscription, RoutingLog, Post
from schemas import AgentRegister, SubscriptionCreate
from auth import get_current_agent
from services.embeddings import embed
from services.safety import validate_webhook_url

router = APIRouter(prefix="/api/v1/agents", tags=["Agents"])


def rebuild_profile(db: Session, agent: Agent):
    """Re-embed the agent's profile (description + interests)."""
    topics = [s.topic for s in db.query(Subscription).filter(Subscription.agent_id == agent.id).all()]
    text = f"{agent.company_name} ({agent.industry}). {agent.description}"
    if topics:
        text += ". Interested in: " + ", ".join(topics)
    agent.interest_embedding = embed(text)
    db.commit()


def agent_view(agent: Agent):
    return {
        "id": agent.id,
        "agent_name": agent.agent_name,
        "company_name": agent.company_name,
        "industry": agent.industry,
        "description": agent.description,
        "webhook_url": agent.webhook_url,
        "is_active": agent.is_active,
        "is_verified": agent.is_verified,
        "trust_score": agent.trust_score,
        "notify_threshold": agent.notify_threshold,
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_agent(agent_data: AgentRegister, db: Session = Depends(get_db)):
    existing = db.query(Agent).filter(
        Agent.agent_name == agent_data.agent_name,
        Agent.company_name == agent_data.company_name,
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="This agent is already registered.")

    webhook_url = str(agent_data.webhook_url) if agent_data.webhook_url else None
    if webhook_url:
        try:
            validate_webhook_url(webhook_url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    api_key = secrets.token_urlsafe(32)
    webhook_secret = secrets.token_hex(24)

    new_agent = Agent(
        agent_name=agent_data.agent_name,
        company_name=agent_data.company_name,
        industry=agent_data.industry,
        description=agent_data.description,
        webhook_url=webhook_url,
        webhook_secret=webhook_secret,
        api_key_hash=hashlib.sha256(api_key.encode()).hexdigest(),
    )
    db.add(new_agent)
    db.flush()  
    for topic in agent_data.interests:
        db.add(Subscription(agent_id=new_agent.id, topic=topic.strip()))
    db.commit()

    rebuild_profile(db, new_agent)
    db.refresh(new_agent)

    return {
        "message": "Agent registered successfully!",
        "agent": agent_view(new_agent),
        "interests": agent_data.interests,
        "api_key": api_key,                
        "webhook_secret": webhook_secret,
    }


@router.get("/me")
def get_agent_profile(current_agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    subs = db.query(Subscription).filter(Subscription.agent_id == current_agent.id).all()
    return {
        "agent": agent_view(current_agent),
        "subscriptions": [{"id": s.id, "topic": s.topic} for s in subs],
    }


@router.post("/regenerate-key")
def regenerate_api_key(current_agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    new_key = secrets.token_urlsafe(32)
    current_agent.api_key_hash = hashlib.sha256(new_key.encode()).hexdigest()
    db.commit()
    return {"message": "API key regenerated successfully!", "api_key": new_key}



@router.post("/me/subscriptions", status_code=201)
def add_subscription(data: SubscriptionCreate,
                     current_agent: Agent = Depends(get_current_agent),
                     db: Session = Depends(get_db)):
    sub = Subscription(agent_id=current_agent.id, topic=data.topic.strip())
    db.add(sub)
    db.commit()
    rebuild_profile(db, current_agent)
    return {"id": sub.id, "topic": sub.topic}


@router.get("/me/subscriptions")
def list_subscriptions(current_agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    subs = db.query(Subscription).filter(Subscription.agent_id == current_agent.id).all()
    return [{"id": s.id, "topic": s.topic} for s in subs]


@router.delete("/me/subscriptions/{sub_id}")
def delete_subscription(sub_id: str,
                        current_agent: Agent = Depends(get_current_agent),
                        db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(
        Subscription.id == sub_id, Subscription.agent_id == current_agent.id
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    db.delete(sub)
    db.commit()
    rebuild_profile(db, current_agent)
    return {"message": "Subscription removed"}


@router.get("/me/notifications")
def my_notifications(only_pending: bool = False,
                     current_agent: Agent = Depends(get_current_agent),
                     db: Session = Depends(get_db)):
    statuses = ["NOTIFIED"] if only_pending else ["NOTIFIED", "ENGAGED", "FAILED"]
    rows = (
        db.query(RoutingLog, Post, Agent)
        .join(Post, RoutingLog.post_id == Post.id)
        .join(Agent, Post.agent_id == Agent.id)
        .filter(RoutingLog.target_agent_id == current_agent.id,
                RoutingLog.status.in_(statuses))
        .order_by(RoutingLog.created_at.desc())
        .all()
    )
    return [
        {
            "post_id": p.id,
            "title": p.title,
            "content": p.content,
            "from_company": a.company_name,
            "relevance_score": l.rerank_score,
            "reason": l.reason,
            "status": l.status,
        }
        for l, p, a in rows
    ]


@router.get("/me/stats")
def my_stats(current_agent: Agent = Depends(get_current_agent), db: Session = Depends(get_db)):
    logs = db.query(RoutingLog).filter(RoutingLog.target_agent_id == current_agent.id).all()
    counts = {"NOTIFIED": 0, "ENGAGED": 0, "SKIPPED": 0, "FAILED": 0}
    for l in logs:
        counts[l.status] = counts.get(l.status, 0) + 1
    delivered = counts["NOTIFIED"] + counts["ENGAGED"]
    return {
        "counts": counts,
        "engagement_rate": round(counts["ENGAGED"] / delivered, 3) if delivered else None,
        "current_threshold": current_agent.notify_threshold,
        "trust_score": current_agent.trust_score,
    }
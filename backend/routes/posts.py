from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Agent, Post, Comment, RoutingLog
from schemas import PostCreate, CommentCreate
from auth import get_current_agent
from services.router_engine import route_and_notify
from services.safety import check_content, check_rate_limit

router = APIRouter(prefix="/api/v1/posts", tags=["Posts"])


@router.post("", status_code=201)
def create_post(post_data: PostCreate,
                background_tasks: BackgroundTasks,
                current_agent: Agent = Depends(get_current_agent),
                db: Session = Depends(get_db)):

    if not check_rate_limit(db, current_agent.id):
        raise HTTPException(status_code=429, detail="Post rate limit exceeded. Try again later.")

    ok, reason = check_content(f"{post_data.title} {post_data.content}")

    new_post = Post(
        title=post_data.title,
        content=post_data.content,
        category=post_data.category,
        agent_id=current_agent.id,        
        status="PUBLISHED" if ok else "FLAGGED",
    )
    if not ok:
        current_agent.trust_score = max(0.1, (current_agent.trust_score or 1.0) - 0.2)

    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    if ok:
        background_tasks.add_task(route_and_notify, new_post.id)

    return {
        "message": "Post created. Routing started." if ok else "Post flagged and not routed.",
        "flag_reason": reason,
        "post": {
            "id": new_post.id,
            "title": new_post.title,
            "content": new_post.content,
            "category": new_post.category,
            "status": new_post.status,
            "agent_id": new_post.agent_id,
            "created_at": new_post.created_at,
        },
    }


@router.get("")
def list_posts(limit: int = 20, db: Session = Depends(get_db)):
    posts = (db.query(Post, Agent).join(Agent, Post.agent_id == Agent.id)
             .filter(Post.status == "PUBLISHED")
             .order_by(Post.created_at.desc()).limit(min(limit, 100)).all())
    return [{"id": p.id, "title": p.title, "content": p.content,
             "company": a.company_name, "created_at": p.created_at} for p, a in posts]


@router.get("/{post_id}")
def get_post(post_id: str, db: Session = Depends(get_db)):
    row = (db.query(Post, Agent).join(Agent, Post.agent_id == Agent.id)
           .filter(Post.id == post_id).first())
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    post, author = row

    comments = (db.query(Comment, Agent).join(Agent, Comment.author_agent_id == Agent.id)
                .filter(Comment.post_id == post_id)
                .order_by(Comment.created_at.asc()).all())
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "status": post.status,
        "company": author.company_name,
        "comments": [{"id": c.id, "company": a.company_name,
                      "content": c.content, "created_at": c.created_at}
                     for c, a in comments],
    }


@router.get("/{post_id}/routing")
def get_routing(post_id: str,
                current_agent: Agent = Depends(get_current_agent),
                db: Session = Depends(get_db)):
    """Explains who was notified and why. Only the post's author can see it."""
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.agent_id != current_agent.id:
        raise HTTPException(status_code=403, detail="Only the author can view routing details")

    rows = (db.query(RoutingLog, Agent).join(Agent, RoutingLog.target_agent_id == Agent.id)
            .filter(RoutingLog.post_id == post_id).all())
    return [{"company": a.company_name, "status": l.status,
             "vector_score": l.vector_score, "final_score": l.rerank_score,
             "reason": l.reason} for l, a in rows]


@router.post("/{post_id}/comments", status_code=201)
def add_comment(post_id: str,
                data: CommentCreate,
                current_agent: Agent = Depends(get_current_agent),
                db: Session = Depends(get_db)):
    post = db.get(Post, post_id)
    if not post or post.status != "PUBLISHED":
        raise HTTPException(status_code=404, detail="Post not found")

    ok, reason = check_content(data.content)
    if not ok:
        raise HTTPException(status_code=400, detail="Comment rejected by moderation.")

    comment = Comment(post_id=post_id, author_agent_id=current_agent.id, content=data.content)
    db.add(comment)

    log = db.query(RoutingLog).filter(
        RoutingLog.post_id == post_id,
        RoutingLog.target_agent_id == current_agent.id,
        RoutingLog.status == "NOTIFIED",
    ).first()
    if log:
        log.status = "ENGAGED"

    db.commit()
    db.refresh(comment)
    return {"message": "Comment added", "comment": {
        "id": comment.id, "post_id": post_id,
        "author_agent_id": current_agent.id, "content": comment.content}}
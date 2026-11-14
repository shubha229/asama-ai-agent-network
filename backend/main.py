from fastapi import FastAPI

from database import Base, engine
import models  
from routes import agents, posts

app = FastAPI(
    title="AI Agent Network API",
    description="A social network where AI agents communicate and collaborate.",
    version="2.0.0",
)

Base.metadata.create_all(bind=engine)

app.include_router(agents.router)
app.include_router(posts.router)


@app.get("/")
def home():
    return {"message": "AI Agent Network API is running", "status": "success"}
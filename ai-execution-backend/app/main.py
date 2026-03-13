from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.db import engine, Base
from app.models.goal import Goal
from app.models.task import Task
from app.models.user import User

from app.api.auth_routes import router as auth_router
from app.api.goal_routes import router as goal_router
from app.api.task_routes import router as task_router

app = FastAPI(title="AI Execution Engine")

Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status":"ok"}

app.include_router(auth_router)
app.include_router(goal_router, prefix="/goals")
app.include_router(task_router, prefix="/tasks")
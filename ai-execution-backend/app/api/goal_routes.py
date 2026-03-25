from datetime import date
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.task import Task
from app.database.db import get_db
from app.models.goal import Goal
from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.ai_service import generate_plan

router = APIRouter()


@router.post("/")
def create_goal(
    goal: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    goal_text = goal.get("goal_text")
    if not goal_text or goal_text.strip() == "":
        raise HTTPException(status_code=400, detail="Goal cannot be empty")

    plan = generate_plan(goal_text)

    goal_obj = Goal(
        goal_text=goal_text,
        plan_summary="",
        user_id=current_user.id
    )

    db.add(goal_obj)
    db.commit()
    db.refresh(goal_obj)

    # Parse the AI plan (it's currently a JSON string)
    parsed_plan = json.loads(plan)

    # Update goal summary
    goal_obj.plan_summary = parsed_plan.get("plan_summary", "")
    db.commit()

    # Insert tasks
    for task in parsed_plan.get("tasks", []):
        task_obj = Task(
            goal_id=goal_obj.id,
            day_number=task.get("day"),
            title=task.get("title"),
            instructions=task.get("instructions"),
            expected_outcome=task.get("expected_outcome"),
            status="PENDING"
        )
        db.add(task_obj)
        db.commit()

    return {
        "goal": goal_text,
        "plan": plan,
        "goal_id": goal_obj.id
    }


@router.get("/tasks")
def get_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tasks = (
        db.query(Task)
        .join(Goal, Task.goal_id == Goal.id)
        .filter(Goal.user_id == current_user.id)
        .all()
    )
    return tasks


@router.get("/{goal_id}/tasks")
def get_tasks_by_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = (
        db.query(Goal)
        .filter(Goal.id == goal_id, Goal.user_id == current_user.id)
        .first()
    )

    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    tasks = db.query(Task).filter(Task.goal_id == goal_id).all()

    return tasks


@router.get("/")
def get_goals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goals = db.query(Goal).filter(Goal.user_id == current_user.id).all()

    result = []

    for goal in goals:
        total_tasks = db.query(Task).filter(Task.goal_id == goal.id).count()

        completed_tasks = db.query(Task).filter(
            Task.goal_id == goal.id,
            Task.status == "COMPLETED"
        ).count()

        result.append({
            "id": goal.id,
            "goal_text": goal.goal_text,
            "status": goal.status,
            "plan_summary": goal.plan_summary,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "start_date": goal.start_date
        })

    return result


@router.patch("/{goal_id}/activate")
def activate_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = (
        db.query(Goal)
        .filter(Goal.id == goal_id, Goal.user_id == current_user.id)
        .first()
    )

    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    goal.status = "ACTIVE"
    goal.start_date = date.today()
    goal.unlocked_until_day = 1

    db.commit()

    return {"message": "Goal activated"}

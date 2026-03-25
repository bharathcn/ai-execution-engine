from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, date
from app.database.db import get_db
from app.models.task import Task
from app.models.goal import Goal
from app.models.user import User
from app.services.auth_service import get_current_user

router = APIRouter()


@router.get("/")
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


@router.patch("/{task_id}/complete")
def complete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = (
        db.query(Task)
        .join(Goal, Task.goal_id == Goal.id)
        .filter(Task.id == task_id, Goal.user_id == current_user.id)
        .first()
    )

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # mark task completed
    task.status = "COMPLETED"
    task.completed_at = datetime.utcnow()

    db.commit()

    # check if any pending tasks remain
    remaining_tasks = db.query(Task).filter(
        Task.goal_id == task.goal_id,
        Task.status == "PENDING"
    ).count()

    # if no tasks left → mark goal completed
    if remaining_tasks == 0:
        goal = db.query(Goal).filter(Goal.id == task.goal_id).first()
        if goal:
            goal.status = "COMPLETED"
            db.commit()

    return {"message": "Task completed"}


@router.get("/goal/{goal_id}/current")
def get_current_task(
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

    task = (
        db.query(Task)
        .filter(Task.goal_id == goal_id, Task.status == "PENDING")
        .order_by(Task.day_number)
        .first()
    )

    if not task:
        return {"message": "GOAL_COMPLETED"}

    return task





@router.get("/today")
def get_today_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goals = (
        db.query(Goal)
        .filter(Goal.status == "ACTIVE", Goal.user_id == current_user.id)
        .all()
    )
    result = []

    for goal in goals:
        if not goal.start_date:
            continue

        current_day = (date.today() - goal.start_date).days + 1
        unlocked_until_day = goal.unlocked_until_day or 1
        allowed_day = max(current_day, unlocked_until_day)

        task = (
            db.query(Task)
            .filter(
                Task.goal_id == goal.id,
                Task.status == "PENDING",
                Task.day_number <= allowed_day
            )
            .order_by(Task.day_number)
            .first()
        )

        if task:
            result.append({
                "id": task.id,
                "title": task.title,
                "day_number": task.day_number,
                "goal_name": goal.goal_text
            })

    return result


@router.patch("/unlock")
def unlock_next_day(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goals = (
        db.query(Goal)
        .filter(Goal.status == "ACTIVE", Goal.user_id == current_user.id)
        .all()
    )

    for goal in goals:
        if not goal.start_date:
            continue

        current_day = (date.today() - goal.start_date).days + 1
        unlocked_until_day = goal.unlocked_until_day or 1
        allowed_day = max(current_day, unlocked_until_day)

        pending_current = db.query(Task).filter(
            Task.goal_id == goal.id,
            Task.status == "PENDING",
            Task.day_number <= allowed_day
        ).count()

        if pending_current == 0:
            goal.unlocked_until_day = allowed_day + 1

    db.commit()
    return {"message": "Next day unlocked"}

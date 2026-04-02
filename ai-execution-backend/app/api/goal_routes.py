import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.goal_config import GOAL_CATEGORIES
from app.models.task import Task
from app.database.db import get_db
from app.models.goal import Goal
from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.goal_service import (
    activate_goal as activate_goal_record,
    create_goal_with_tasks,
    detect_category,
    generate_plan_payload,
    load_goal_answers,
    normalize_category,
    save_tasks,
)

router = APIRouter()


def _get_owned_goal(db: Session, current_user: User, goal_id: int) -> Goal:
    goal = (
        db.query(Goal)
        .filter(Goal.id == goal_id, Goal.user_id == current_user.id)
        .first()
    )

    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    return goal


def _get_owned_draft_goal(db: Session, current_user: User, goal_id: int) -> Goal:
    goal = _get_owned_goal(db, current_user, goal_id)

    if goal.status != "DRAFT":
        raise HTTPException(
            status_code=400,
            detail="Only draft goals can be approved or regenerated",
        )

    return goal


@router.post("/intake/start")
def start_goal_intake(data: dict):
    goal_text = data.get("goal_text")
    if not isinstance(goal_text, str):
        goal_text = str(goal_text or "")

    if not goal_text.strip():
        raise HTTPException(status_code=400, detail="goal_text is required")

    category = detect_category(goal_text)
    questions = GOAL_CATEGORIES.get(category, {}).get("questions", [])

    return {
        "category": category,
        "questions": questions,
    }


@router.post("/intake/complete")
def complete_goal_intake(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal_text = data.get("goal_text")
    if not isinstance(goal_text, str):
        goal_text = str(goal_text or "")

    if not goal_text.strip():
        raise HTTPException(status_code=400, detail="goal_text is required")

    try:
        plan_payload = generate_plan_payload(
            goal_text,
            category=data.get("category"),
            answers=data.get("answers", {}),
        )
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Failed to generate valid tasks") from exc

    goal_obj = create_goal_with_tasks(
        db=db,
        current_user=current_user,
        goal_text=goal_text,
        tasks_data=plan_payload["tasks"],
        category=plan_payload["category"],
        answers=plan_payload["answers"],
        status="DRAFT",
        plan_summary=plan_payload["plan_summary"],
    )

    return {"goal_id": goal_obj.id, "tasks": plan_payload["tasks"]}


@router.post("/{goal_id}/approve")
def approve_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = _get_owned_draft_goal(db, current_user, goal_id)

    activate_goal_record(goal)
    db.commit()

    return {"message": "Goal approved successfully"}


@router.post("/{goal_id}/regenerate")
def regenerate_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = _get_owned_draft_goal(db, current_user, goal_id)

    category = normalize_category(goal.goal_text, goal.category)
    answers = load_goal_answers(goal)

    try:
        plan_payload = generate_plan_payload(
            goal.goal_text,
            category=category,
            answers=answers,
        )
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Failed to generate valid tasks") from exc

    db.query(Task).filter(Task.goal_id == goal.id).delete()
    db.commit()

    save_tasks(db, goal.id, plan_payload["tasks"])
    goal.plan_summary = plan_payload["plan_summary"]
    db.commit()

    return {"goal_id": goal.id, "tasks": plan_payload["tasks"]}


@router.post("/")
def create_goal(
    goal: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal_text = goal.get("goal_text")
    if not isinstance(goal_text, str):
        goal_text = str(goal_text or "")
    if not goal_text or goal_text.strip() == "":
        raise HTTPException(status_code=400, detail="Goal cannot be empty")

    try:
        plan_payload = generate_plan_payload(
            goal_text,
            category=goal.get("category"),
            answers=goal.get("answers") or {},
        )
        plan = json.dumps(
            {
                "plan_summary": plan_payload["plan_summary"],
                "tasks": plan_payload["tasks"],
            }
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail="Failed to generate a valid execution plan",
        ) from exc

    goal_obj = create_goal_with_tasks(
        db=db,
        current_user=current_user,
        goal_text=goal_text,
        tasks_data=plan_payload["tasks"],
        category=plan_payload["category"],
        answers=plan_payload["answers"],
        plan_summary=plan_payload["plan_summary"],
    )

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
    goal = _get_owned_goal(db, current_user, goal_id)

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
    goal = _get_owned_goal(db, current_user, goal_id)

    activate_goal_record(goal)
    db.commit()

    return {"message": "Goal activated"}

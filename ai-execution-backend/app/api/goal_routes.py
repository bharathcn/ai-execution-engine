from datetime import date
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.goal_config import GOAL_CATEGORIES
from app.models.task import Task
from app.database.db import get_db
from app.models.goal import Goal
from app.models.user import User
from app.services.ai_service import build_prompt, generate_plan, generate_tasks_from_ai
from app.services.auth_service import get_current_user
from app.services.goal_service import detect_category

router = APIRouter()


def _save_tasks(db: Session, goal_id: int, tasks_data: list[dict]) -> None:
    task_objects = []
    for task in tasks_data:
        task_objects.append(
            Task(
                goal_id=goal_id,
                day_number=task["day_number"],
                title=task["title"],
                instructions=task["instructions"],
                expected_outcome=task["expected_outcome"],
                status="PENDING",
            )
        )

    db.add_all(task_objects)
    db.commit()


def _create_goal_with_tasks(
    db: Session,
    current_user: User,
    goal_text: str,
    tasks_data: list[dict],
    *,
    category: str | None = None,
    answers: dict | None = None,
    status: str = "DRAFT",
) -> Goal:
    goal_obj = Goal(
        goal_text=goal_text,
        category=category,
        answers_json=json.dumps(answers or {}),
        plan_summary="",
        status=status,
        user_id=current_user.id,
    )
    db.add(goal_obj)
    db.commit()
    db.refresh(goal_obj)

    _save_tasks(db, goal_obj.id, tasks_data)

    return goal_obj


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


def _load_goal_answers(goal: Goal) -> dict:
    if not goal.answers_json:
        return {}

    try:
        parsed_answers = json.loads(goal.answers_json)
    except json.JSONDecodeError:
        return {}

    return parsed_answers if isinstance(parsed_answers, dict) else {}


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

    category = data.get("category")
    if not isinstance(category, str) or category not in GOAL_CATEGORIES:
        category = detect_category(goal_text)

    answers = data.get("answers", {})
    if not isinstance(answers, dict):
        answers = {}

    prompt = build_prompt(goal_text, category, answers)

    try:
        tasks_data = generate_tasks_from_ai(prompt)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Failed to generate valid tasks") from exc

    goal_obj = _create_goal_with_tasks(
        db=db,
        current_user=current_user,
        goal_text=goal_text,
        tasks_data=tasks_data,
        category=category,
        answers=answers,
        status="DRAFT",
    )

    return {"goal_id": goal_obj.id, "tasks": tasks_data}


@router.post("/{goal_id}/approve")
def approve_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = _get_owned_draft_goal(db, current_user, goal_id)

    goal.status = "ACTIVE"
    goal.start_date = date.today()
    goal.unlocked_until_day = 1

    db.commit()

    return {"message": "Goal approved successfully"}


@router.post("/{goal_id}/regenerate")
def regenerate_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = _get_owned_draft_goal(db, current_user, goal_id)

    category = goal.category or detect_category(goal.goal_text)
    answers = _load_goal_answers(goal)
    prompt = build_prompt(goal.goal_text, category, answers)

    try:
        tasks_data = generate_tasks_from_ai(prompt)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Failed to generate valid tasks") from exc

    db.query(Task).filter(Task.goal_id == goal.id).delete()
    db.commit()

    _save_tasks(db, goal.id, tasks_data)

    return {"goal_id": goal.id, "tasks": tasks_data}


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

    category = goal.get("category") or "General"
    if not isinstance(category, str):
        category = str(category)

    answers = goal.get("answers") or {}

    try:
        plan = generate_plan(goal_text, category=category, answers=answers)
        parsed_plan = json.loads(plan)
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Failed to generate a valid execution plan",
        ) from exc

    goal_obj = _create_goal_with_tasks(
        db=db,
        current_user=current_user,
        goal_text=goal_text,
        tasks_data=parsed_plan.get("tasks", []),
        category=category,
        answers=answers if isinstance(answers, dict) else {},
    )

    # Update goal summary
    goal_obj.plan_summary = parsed_plan.get("plan_summary", "")
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

    goal.status = "ACTIVE"
    goal.start_date = date.today()
    goal.unlocked_until_day = 1

    db.commit()

    return {"message": "Goal activated"}

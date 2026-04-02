from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.goal import Goal
from app.models.task import Task
from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.task_assist_service import assist_with_task

router = APIRouter()


class TaskAssistRequest(BaseModel):
    message: str


class TaskSubmissionRequest(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)


def _get_task(task_id: int, db: Session) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


def _get_owned_task(task_id: int, db: Session, current_user: User) -> Task:
    task = _get_task(task_id, db)

    goal = (
        db.query(Goal)
        .filter(Goal.id == task.goal_id)
        .first()
    )

    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    if goal.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this task")

    return task


def _complete_task_and_goal(db: Session, task: Task) -> dict[str, Any]:
    if task.status != "COMPLETED":
        task.status = "COMPLETED"
        task.completed_at = datetime.utcnow()
        db.add(task)
        db.commit()
        db.refresh(task)

    remaining_tasks = db.query(Task).filter(
        Task.goal_id == task.goal_id,
        Task.status == "PENDING",
    ).count()

    if remaining_tasks == 0:
        goal = db.query(Goal).filter(Goal.id == task.goal_id).first()
        if goal and goal.status != "COMPLETED":
            goal.status = "COMPLETED"
            db.add(goal)
            db.commit()

    return {"message": "Task completed", "task_id": task.id}


def _get_input_schema_fields(task: Task) -> list[dict[str, Any]]:
    input_schema = task.input_schema if isinstance(task.input_schema, dict) else None
    fields = input_schema.get("fields") if input_schema else None

    if not isinstance(fields, list):
        return []

    return [field for field in fields if isinstance(field, dict)]


def _coerce_checkbox_value(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False

    return None


def _validate_task_inputs(task: Task, inputs: dict[str, Any]) -> dict[str, Any]:
    fields = _get_input_schema_fields(task)
    if not fields:
        raise HTTPException(
            status_code=400,
            detail="This task does not accept structured input submission.",
        )

    errors: list[str] = []
    cleaned_inputs: dict[str, Any] = {}

    for field in fields:
        field_name = str(field.get("name") or "").strip()
        label = str(field.get("label") or field_name or "Field").strip()
        field_type = str(field.get("type") or "text").strip().lower()
        required = bool(field.get("required"))
        raw_value = inputs.get(field_name)

        if field_type == "checkbox":
            parsed_value = _coerce_checkbox_value(raw_value)
            if required and parsed_value is not True:
                errors.append(f"{label} must be checked.")
            elif parsed_value is not None:
                cleaned_inputs[field_name] = parsed_value
            continue

        if raw_value is None:
            text_value = ""
        else:
            text_value = str(raw_value).strip()

        if required and not text_value:
            errors.append(f"{label} is required.")
            continue

        if not text_value:
            continue

        if field_type == "number":
            try:
                number_value = float(text_value)
            except ValueError:
                errors.append(f"{label} must be a valid number.")
                continue

            cleaned_inputs[field_name] = int(number_value) if number_value.is_integer() else number_value
            continue

        if field_type == "date":
            try:
                datetime.fromisoformat(text_value)
            except ValueError:
                errors.append(f"{label} must be a valid date.")
                continue

            cleaned_inputs[field_name] = text_value
            continue

        if field_type == "select":
            options = field.get("options")
            valid_options = (
                [str(option) for option in options if str(option).strip()]
                if isinstance(options, list)
                else []
            )
            if text_value not in valid_options:
                errors.append(f"{label} must be one of the provided options.")
                continue

        cleaned_inputs[field_name] = text_value

    if errors:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Please fix the required task inputs.",
                "errors": errors,
            },
        )

    return cleaned_inputs


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
    task = _get_owned_task(task_id, db, current_user)
    if _get_input_schema_fields(task):
        raise HTTPException(
            status_code=400,
            detail="This task requires structured input. Submit the task form to complete it.",
        )

    return _complete_task_and_goal(db, task)


@router.post("/{task_id}/submit")
def submit_task(
    task_id: int,
    data: TaskSubmissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_owned_task(task_id, db, current_user)
    cleaned_inputs = _validate_task_inputs(task, data.inputs)
    response = _complete_task_and_goal(db, task)
    response["submitted_inputs"] = cleaned_inputs
    return response


@router.post("/{task_id}/chat")
def task_chat(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_task(task_id, db, current_user)
    raise HTTPException(
        status_code=410,
        detail="Task chat has moved. Use /tasks/{task_id}/assist for task-level execution help.",
    )


@router.post("/{task_id}/assist")
def task_assist(
    task_id: int,
    data: TaskAssistRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_owned_task(task_id, db, current_user)

    if not data.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    return assist_with_task(
        db,
        task=task,
        user=current_user,
        message=data.message,
    )


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
                "goal_name": goal.goal_text,
                "instructions": task.instructions,
                "expected_outcome": task.expected_outcome,
                "input_schema": task.input_schema,
                "requires_input": bool(_get_input_schema_fields(task)),
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

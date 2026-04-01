import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_CATEGORY = "General"
DEFAULT_SEED = int(os.getenv("OPENAI_SEED", "42"))


def format_answers(answers: dict) -> str:
    return "\n".join(
        [f"{key.replace('_', ' ').title()}: {value}" for key, value in answers.items()]
    )


def build_prompt(goal_text: str, category: str, answers: dict) -> str:
    formatted_answers = format_answers(answers)

    return f"""### ROLE

You are an expert execution coach who specializes in turning goals into step-by-step actionable plans.

---

### OBJECTIVE

Generate a structured execution plan for the given goal.

---

### CONTEXT

Goal: {goal_text}
Category: {category}

---

### USER INPUT

{formatted_answers}

---

### TASK GENERATION RULES

* Break the goal into daily actionable tasks
* Each task must:

  * Be specific and practical
  * Be completable within a day
  * Focus on execution, not theory
* Tasks must follow a logical progression (beginner → advanced)
* Avoid repetition
* Avoid vague tasks like "research more"
* Ensure tasks align with user inputs (duration, experience, etc.)

---

### OUTPUT FORMAT (STRICT)

Return ONLY valid JSON.

[
{{
"day_number": 1,
"title": "Short actionable title",
"instructions": "Step-by-step guidance",
"expected_outcome": "Clear measurable result"
}}
]

---

### HARD CONSTRAINTS

* Do NOT include explanations
* Do NOT include markdown
* Do NOT include extra text
* Output must be parseable JSON only
* Ensure day_number starts from 1 and increments sequentially
* Number of tasks should align with duration if provided, but can be flexible

---"""


def build_task_chat_prompt(task: Any, user_message: str) -> str:
    return f"""You are an execution assistant helping a user complete a task.

---

### TASK CONTEXT

Task: {task.title}
Instructions: {task.instructions}
Expected Outcome: {task.expected_outcome}

---

### RULES

* Only respond within this task context
* Do NOT provide unrelated advice
* Guide step-by-step
* Be concise and practical
* If user asks unrelated question, redirect back to task

---

### USER MESSAGE

{user_message}
"""


def _normalize_tasks(parsed_response: Any) -> list[dict[str, Any]]:
    tasks = parsed_response.get("tasks") if isinstance(parsed_response, dict) else parsed_response

    if not isinstance(tasks, list):
        raise ValueError("AI response must be a JSON array of tasks.")

    normalized_tasks: list[dict[str, Any]] = []

    for expected_day_number, task in enumerate(tasks, start=1):
        if not isinstance(task, dict):
            raise ValueError("Each generated task must be a JSON object.")

        raw_day_number = task.get("day_number", task.get("day"))

        if raw_day_number is None:
            raise ValueError("Each task must include day_number.")

        try:
            day_number = int(raw_day_number)
        except (TypeError, ValueError) as exc:
            raise ValueError("day_number must be an integer.") from exc

        if day_number != expected_day_number:
            raise ValueError("day_number values must start at 1 and increment sequentially.")

        title = str(task.get("title", "")).strip()
        instructions = str(task.get("instructions", "")).strip()
        expected_outcome = str(task.get("expected_outcome", "")).strip()

        if not title or not instructions or not expected_outcome:
            raise ValueError("Each task must include title, instructions, and expected_outcome.")

        normalized_tasks.append(
            {
                "day": day_number,
                "day_number": day_number,
                "title": title,
                "instructions": instructions,
                "expected_outcome": expected_outcome,
            }
        )

    return normalized_tasks


def generate_tasks_from_ai(prompt: str) -> list[dict[str, Any]]:
    last_error: Exception | None = None

    for attempt in range(2):
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            temperature=0,
            seed=DEFAULT_SEED,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_response = response.choices[0].message.content or ""

        try:
            return _normalize_tasks(json.loads(raw_response.strip()))
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            last_error = exc
            logger.exception(
                "Failed to parse AI task response on attempt %s. Raw response: %s",
                attempt + 1,
                raw_response,
            )

    raise ValueError("Failed to generate valid tasks.") from last_error


def generate_plan(goal_text: str, category: str = DEFAULT_CATEGORY, answers: dict | None = None) -> str:
    safe_category = category.strip() if category and category.strip() else DEFAULT_CATEGORY
    safe_answers = answers if isinstance(answers, dict) else {}
    prompt = build_prompt(goal_text=goal_text.strip(), category=safe_category, answers=safe_answers)
    tasks = generate_tasks_from_ai(prompt)

    return json.dumps(
        {
            "plan_summary": "",
            "tasks": tasks,
        }
    )


def generate_task_chat_response(prompt: str) -> str:
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        temperature=0,
        seed=DEFAULT_SEED,
        messages=[{"role": "user", "content": prompt}],
    )

    return (response.choices[0].message.content or "").strip()

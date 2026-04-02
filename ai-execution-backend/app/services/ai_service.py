import json
import logging
import os
import re
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_CATEGORY = "General"
DEFAULT_SEED = int(os.getenv("OPENAI_SEED", "42"))
SUPPORTED_INPUT_TYPES = {"text", "textarea", "number", "date", "select", "checkbox"}


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
* Add `input_schema` ONLY when the task can be completed through a small deterministic form
* Use `input_schema: null` for tasks that require research, conversation, troubleshooting, reflection, or open-ended execution
* When `input_schema` is present, use this exact shape:
  {{
    "submit_label": "Submit and complete",
    "fields": [
      {{
        "name": "field_name",
        "label": "Field label",
        "type": "text | textarea | number | date | select | checkbox",
        "required": true,
        "placeholder": "Optional placeholder",
        "help_text": "Optional short guidance",
        "options": ["Only for select inputs"]
      }}
    ]
  }}
* Keep form fields minimal and practical
* Never use chat-style prompts inside `input_schema`

---

### OUTPUT FORMAT (STRICT)

Return ONLY valid JSON.

[
{{
"day_number": 1,
"title": "Short actionable title",
"instructions": "Step-by-step guidance",
"expected_outcome": "Clear measurable result",
"input_schema": null
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


def _slugify_field_name(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return slug.strip("_")


def _normalize_input_field(field: Any) -> dict[str, Any] | None:
    if not isinstance(field, dict):
        return None

    raw_name = str(field.get("name") or "").strip()
    raw_label = str(field.get("label") or "").strip()
    field_name = _slugify_field_name(raw_name or raw_label)

    if not field_name:
        return None

    field_type = str(field.get("type") or "text").strip().lower()
    if field_type not in SUPPORTED_INPUT_TYPES:
        field_type = "text"

    normalized_field: dict[str, Any] = {
        "name": field_name,
        "label": raw_label or field_name.replace("_", " ").title(),
        "type": field_type,
        "required": bool(field.get("required")),
    }

    placeholder = str(field.get("placeholder") or "").strip()
    if placeholder:
        normalized_field["placeholder"] = placeholder

    help_text = str(field.get("help_text") or field.get("helper_text") or "").strip()
    if help_text:
        normalized_field["help_text"] = help_text

    if field_type == "select":
        raw_options = field.get("options")
        if isinstance(raw_options, list):
            options = [
                str(option).strip()
                for option in raw_options
                if str(option).strip()
            ]
        else:
            options = []

        if not options:
            return None

        normalized_field["options"] = options

    return normalized_field


def _normalize_input_schema(raw_input_schema: Any) -> dict[str, Any] | None:
    if raw_input_schema in (None, False, ""):
        return None

    if not isinstance(raw_input_schema, dict):
        return None

    raw_fields = raw_input_schema.get("fields")
    if not isinstance(raw_fields, list):
        return None

    normalized_fields = []
    for field in raw_fields[:6]:
        normalized_field = _normalize_input_field(field)
        if normalized_field:
            normalized_fields.append(normalized_field)

    if not normalized_fields:
        return None

    submit_label = str(raw_input_schema.get("submit_label") or "").strip()

    return {
        "submit_label": submit_label or "Submit and complete",
        "fields": normalized_fields,
    }

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
                "input_schema": _normalize_input_schema(task.get("input_schema")),
            }
        )

    return normalized_tasks
def _request_json(prompt: str) -> Any:
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        temperature=0,
        seed=DEFAULT_SEED,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_response = response.choices[0].message.content or ""

    return json.loads(raw_response.strip())


def generate_tasks_from_ai(prompt: str) -> list[dict[str, Any]]:
    last_error: Exception | None = None

    for attempt in range(2):
        try:
            return _normalize_tasks(_request_json(prompt))
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            last_error = exc
            logger.exception(
                "Failed to parse AI task response on attempt %s.",
                attempt + 1,
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

# AI Execution Engine – Repository Context

## Project Purpose
This project is an AI-powered execution assistant that converts goals into structured daily tasks and ensures users focus on one task at a time until completion.

The system prevents distraction and hallucination-heavy AI workflows by enforcing sequential execution.

Example workflow:
1. User creates a goal
2. AI generates a 7-day execution plan
3. User approves the plan
4. Goal becomes ACTIVE
5. Only the next task in sequence is shown
6. After finishing a task, the user can unlock the next task

---

# Architecture Overview

Frontend:
Next.js (React)
Location:
ai-execution-frontend/

Main components:
- TodayTasks.tsx → shows current tasks to execute
- GoalForm.tsx → create goal and approve plan
- GoalsList.tsx → shows all goals and progress
- Home.tsx → dashboard layout and refresh triggers

Frontend responsibilities:
- Show one task at a time
- Track progress
- Allow unlocking next day tasks
- Display goal progress

---

Backend:
FastAPI
Location:
ai-execution-backend/

Key routes:
POST /goals
Create goal and generate AI plan

PATCH /goals/{goal_id}/activate
Activate goal and set start_date

GET /tasks/today
Returns the next pending task for each active goal

PATCH /tasks/{task_id}/complete
Marks a task as completed

GET /goals
Returns all goals with progress

GET /goals/{goal_id}/tasks
Returns all tasks for a goal

---

Database:
SQLite with SQLAlchemy

Tables:

goals
- id
- goal_text
- status (DRAFT | ACTIVE | COMPLETED)
- plan_summary
- start_date
- created_at

tasks
- id
- goal_id
- title
- instructions
- expected_outcome
- day_number
- status (PENDING | COMPLETED)
- created_at
- completed_at

---

Task Execution Rules

Sequential task logic:

A task is visible if:
task.day_number <= current_day

Where:
current_day = (today - goal.start_date) + 1

Manual unlock allows:
task.day_number <= current_day + 1

Only one pending task per goal is returned.

---

Frontend Execution Logic

TodayTasks component:
- loads tasks using /tasks/today
- tracks completed tasks locally
- shows "Day Completed" when all tasks done
- Unlock Next Day loads next sequential tasks

GoalForm component:
- creates goal
- displays generated plan
- user approves plan
- activates goal
- triggers TodayTasks refresh

---

Design Philosophy

The system is built to enforce execution discipline.

Principles:
- show only the next actionable task
- avoid overwhelming task lists
- encourage daily progress
- allow manual override via unlock

---

Known Future Improvements

Planned features:

1. Calendar heatmap (task streaks)
2. Goal grouping in Today's Focus
3. Goal progress ring visualization
4. User authentication
5. SaaS multi-user support
6. AI reflection / daily feedback
7. Productivity analytics
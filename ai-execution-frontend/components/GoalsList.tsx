"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../lib/api";

type Goal = {
  id: number;
  goal_text: string;
  status: "ACTIVE" | "DRAFT" | "COMPLETED";
  total_tasks: number;
  completed_tasks: number;
};

type GoalTask = {
  id: number;
  day_number: number;
  title: string;
  status: "PENDING" | "COMPLETED";
};

function ProgressRing({ progress }: { progress: number }) {

  const radius = 14
  const stroke = 3
  const normalizedRadius = radius - stroke * 2
  const circumference = normalizedRadius * 2 * Math.PI

  const strokeDashoffset =
    circumference - progress / 100 * circumference

  return (
    <svg
      className="progress-ring"
      height={radius * 2}
      width={radius * 2}
    >
      <circle
        stroke="#e5e7eb"
        fill="transparent"
        strokeWidth={stroke}
        r={normalizedRadius}
        cx={radius}
        cy={radius}
      />

      <circle
        stroke="#4f46e5"
        fill="transparent"
        strokeWidth={stroke}
        strokeDasharray={`${circumference} ${circumference}`}
        style={{
          strokeDashoffset,
          transform:"rotate(-90deg)",
          transformOrigin:"50% 50%"
        }}
        r={normalizedRadius}
        cx={radius}
        cy={radius}
      />
    </svg>
  )
}

export default function YourGoals({ refreshTrigger }: any) {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [visibleCount, setVisibleCount] = useState(5);

  const [expandedGoal, setExpandedGoal] = useState<number | null>(null);
  const [goalTasks, setGoalTasks] = useState<Record<number, GoalTask[]>>({});

  function loadGoals() {
    apiFetch("/goals")
      .then((res) => res.json())
      .then((data) => {
        const active = data.filter((g) => g.status === "ACTIVE");
        const draft = data.filter((g) => g.status === "DRAFT");
        const completed = data.filter((g) => g.status === "COMPLETED");

        const ordered = [...active.reverse(), ...draft.reverse(), ...completed];

        setGoals(ordered);
      });
  }

  useEffect(() => {
    loadGoals();
  }, [refreshTrigger]);

  function toggleGoal(goalId: number) {
    if (expandedGoal === goalId) {
      setExpandedGoal(null);
      return;
    }

    setExpandedGoal(goalId);

    if (!goalTasks[goalId]) {
      apiFetch(`/goals/${goalId}/tasks`)
        .then((res) => res.json())
        .then((data) => {
          const tasksArray = Array.isArray(data) ? data : [];

          setGoalTasks((prev) => ({
            ...prev,
            [goalId]: tasksArray,
          }));
        });
    }
  }

  return (
    <div>
      <h2>Your Goals</h2>

      {goals.slice(0, visibleCount).map((goal) => {
        const progress =
          goal.total_tasks === 0
            ? 0
            : (goal.completed_tasks / goal.total_tasks) * 100;
        const tasksForGoal = Array.isArray(goalTasks[goal.id])
          ? goalTasks[goal.id]
          : [];

        return (
          <div
            key={goal.id}
            className="goal-card"
            style={{
              opacity: goal.status === "COMPLETED" ? 0.6 : 1,
            }}
          >
            <button
              type="button"
              className="goal-toggle"
              onClick={() => toggleGoal(goal.id)}
            >
              <div className="goal-summary-row">
                <ProgressRing progress={progress} />
                <div className="goal-summary-main">
                  <div className="goal-heading-row">
                    <strong className="goal-title">{goal.goal_text}</strong>

                    {goal.status === "ACTIVE" && (
                      <span className="badge badge-active">ACTIVE</span>
                    )}

                    {goal.status === "DRAFT" && (
                      <span className="badge badge-draft">DRAFT</span>
                    )}

                    {goal.status === "COMPLETED" && (
                      <span className="badge badge-completed">✔</span>
                    )}
                  </div>

                  <div className="goal-progress-text">
                    {goal.completed_tasks} / {goal.total_tasks} tasks
                  </div>
                </div>
              </div>
            </button>

            {expandedGoal === goal.id && tasksForGoal.length > 0 && (
              <div className="goal-task-list">
                {tasksForGoal.map((task) => (
                  <div
                    key={task.id}
                    className={`goal-task-item ${task.status === "COMPLETED" ? "goal-task-item-completed" : ""}`}
                  >
                    {task.status === "COMPLETED" ? "✔ " : "○ "}Day{" "}
                    {task.day_number} - {task.title}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}

      {visibleCount < goals.length && (
        <button
          className="load-more-button"
          onClick={() => setVisibleCount((prev) => prev + 5)}
        >
          Load More Goals
        </button>
      )}
    </div>
  );
}

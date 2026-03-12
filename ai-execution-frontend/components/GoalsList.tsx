"use client";

import { useEffect, useState } from "react";

function ProgressRing({ progress }) {

  const radius = 14
  const stroke = 3
  const normalizedRadius = radius - stroke * 2
  const circumference = normalizedRadius * 2 * Math.PI

  const strokeDashoffset =
    circumference - progress / 100 * circumference

  return (
    <svg
      height={radius * 2}
      width={radius * 2}
      style={{marginRight:"8px"}}
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
  const [goals, setGoals] = useState([]);
  const [visibleCount, setVisibleCount] = useState(5);

  const [expandedGoal, setExpandedGoal] = useState(null);
  const [goalTasks, setGoalTasks] = useState({});

  function loadGoals() {
    fetch("http://localhost:8000/goals")
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

  function toggleGoal(goalId) {
    if (expandedGoal === goalId) {
      setExpandedGoal(null);
      return;
    }

    setExpandedGoal(goalId);

    if (!goalTasks[goalId]) {
      fetch(`http://localhost:8000/goals/${goalId}/tasks`)
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

        return (
          <div
            key={goal.id}
            className="goal-card"
            style={{
              opacity: goal.status === "COMPLETED" ? 0.6 : 1,
            }}
          >
            <div
              style={{ cursor: "pointer" }}
              onClick={() => toggleGoal(goal.id)}
            >
              <div
                style={{ display: "flex", alignItems: "center", gap: "8px" }}
              >
                <ProgressRing progress={progress} />
                <strong>{goal.goal_text}</strong>

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

              <div style={{ fontSize: "13px", color: "#666" }}>
                {goal.completed_tasks} / {goal.total_tasks} tasks
              </div>
            </div>

            {expandedGoal === goal.id && goalTasks[goal.id] && (
              <div style={{ marginTop: "10px" }}>
                {(Array.isArray(goalTasks[goal.id])
                  ? goalTasks[goal.id]
                  : []
                ).map((task) => (
                  <div
                    key={task.id}
                    style={{
                      fontSize: "13px",
                      marginBottom: "4px",
                      color: task.status === "COMPLETED" ? "#16a34a" : "#555",
                    }}
                  >
                    {task.status === "COMPLETED" ? "✔ " : "○ "}
                    Day {task.day_number} — {task.title}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}

      {visibleCount < goals.length && (
        <button
          style={{ marginTop: "15px" }}
          onClick={() => setVisibleCount((prev) => prev + 5)}
        >
          Load More Goals
        </button>
      )}
    </div>
  );
}

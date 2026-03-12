"use client";

import { useEffect, useState } from "react";

export default function TodayTasks({ refreshTrigger, onTaskComplete }: any) {
  const [tasks, setTasks] = useState<any[]>([]);
  const [completed, setCompleted] = useState(0);
  const [dayCompleted, setDayCompleted] = useState(false);
  const [initialCount, setInitialCount] = useState(0);
  const [removingTask, setRemovingTask] = useState<number | null>(null);

  function loadTasks() {
    fetch("http://localhost:8000/tasks/today")
      .then((res) => res.json())
      .then((data) => {
        setTasks(data);
        setInitialCount(data.length);
        setCompleted(0);
        setDayCompleted(false);
      });
  }

  async function unlockNextDay() {
    await fetch("http://localhost:8000/tasks/unlock", {
      method: "PATCH",
    });

    fetch("http://localhost:8000/tasks/today")
      .then((res) => res.json())
      .then((data) => {
        setTasks(data);
        setInitialCount(data.length);
        setCompleted(0);
        setDayCompleted(false);
      });
  }

  useEffect(() => {
    loadTasks();
  }, [refreshTrigger]);

  const progress = initialCount === 0 ? 0 : (completed / initialCount) * 100;

  function completeTask(taskId: number) {
    const remainingVisibleTasks = tasks.length;

    fetch(`http://localhost:8000/tasks/${taskId}/complete`, {
      method: "PATCH",
    }).then(() => {
      setRemovingTask(taskId);

      setTimeout(() => {
        setTasks((prev) => prev.filter((task) => task.id !== taskId));
        setRemovingTask(null);
      }, 250);

      setCompleted((prev) => prev + 1);

      if (remainingVisibleTasks === 1) {
        setDayCompleted(true);
      }

      if (onTaskComplete) {
        onTaskComplete();
      }
    });
  }

  return (
    <div>
      <h2>Today's Focus</h2>

      <div style={{ marginBottom: "20px" }}>
        <div style={{ fontSize: "14px", marginBottom: "6px" }}>
          Today's Progress ({completed}/{initialCount})
        </div>

        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progress}%` }} />
        </div>
      </div>

      {dayCompleted && (
        <div className="goal-card" style={{ background: "#f0fdf4" }}>
          <h3 style={{ margin: "0 0 10px 0" }}>Day Completed</h3>
          <button onClick={unlockNextDay}>Unlock Next Day</button>
        </div>
      )}

      {!dayCompleted &&
        tasks.map((task) => (
          <div
            key={task.id}
            className={`goal-card ${removingTask === task.id ? "task-fade-out" : ""}`}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <strong>{task.title}</strong>

              <div style={{ fontSize: "13px", color: "#666" }}>
                Day {task.day_number}
              </div>

              <div style={{ fontSize: "12px", color: "#888" }}>
                Goal: {task.goal_name}
              </div>
            </div>

            <button
              style={{
                background: "#10b981",
                padding: "6px 12px",
                fontSize: "13px",
              }}
              onClick={() => completeTask(task.id)}
            >
              Done
            </button>
          </div>
        ))}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../lib/api";
import TaskExecutionCard, { type TodayTask } from "./TaskExecutionCard";
import TaskFocusChat from "./TaskFocusChat";

type ChatMessage = {
  role: "user" | "ai";
  text: string;
};

export default function TodayTasks({ refreshTrigger, onTaskComplete }: any) {
  const [tasks, setTasks] = useState<TodayTask[]>([]);
  const [completed, setCompleted] = useState(0);
  const [dayCompleted, setDayCompleted] = useState(false);
  const [initialCount, setInitialCount] = useState(0);
  const [removingTask, setRemovingTask] = useState<number | null>(null);
  const [activeTaskId, setActiveTaskId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  function loadTasks() {
    apiFetch("/tasks/today")
      .then((res) => res.json())
      .then((data) => {
        const nextTasks = Array.isArray(data) ? data : [];

        setTasks(nextTasks);
        setInitialCount(nextTasks.length);
        setCompleted(0);
        setDayCompleted(false);
        setActiveTaskId((prev) => {
          const nextActiveTaskId = nextTasks.some((task) => task.id === prev)
            ? prev
            : null;

          if (nextActiveTaskId === null) {
            setMessages([]);
          }

          return nextActiveTaskId;
        });
      });
  }

  async function unlockNextDay() {
    await apiFetch("/tasks/unlock", {
      method: "PATCH",
    });

    apiFetch("/tasks/today")
      .then((res) => res.json())
      .then((data) => {
        const nextTasks = Array.isArray(data) ? data : [];

        setTasks(nextTasks);
        setInitialCount(nextTasks.length);
        setCompleted(0);
        setDayCompleted(false);
      });
  }

  useEffect(() => {
    loadTasks();
  }, [refreshTrigger]);

  const progress = initialCount === 0 ? 0 : (completed / initialCount) * 100;
  const activeTask = tasks.find((task) => task.id === activeTaskId) || null;

  function openChat(taskId: number) {
    setActiveTaskId(taskId);
    setMessages([]);
  }

  function handleTaskCompleted(taskId: number) {
    const remainingVisibleTasks = tasks.length;

    setRemovingTask(taskId);

    setTimeout(() => {
      setTasks((prev) => prev.filter((task) => task.id !== taskId));
      setRemovingTask(null);
    }, 250);

    if (activeTaskId === taskId) {
      setActiveTaskId(null);
      setMessages([]);
    }

    setCompleted((prev) => prev + 1);

    if (remainingVisibleTasks === 1) {
      setDayCompleted(true);
    }

    if (onTaskComplete) {
      onTaskComplete();
    }
  }

  return (
    <div>
      <h2>Today's Focus</h2>

      <div className="progress-section">
        <div className="progress-label">
          Today's Progress ({completed}/{initialCount})
        </div>

        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progress}%` }} />
        </div>
      </div>

      {dayCompleted && (
        <div className="goal-card success-card">
          <h3 className="success-card-title">Day Completed</h3>
          <button onClick={unlockNextDay}>Unlock Next Day</button>
        </div>
      )}

      {!dayCompleted &&
        tasks.map((task) => (
          <TaskExecutionCard
            key={task.id}
            task={task}
            helpOpen={activeTaskId === task.id}
            isRemoving={removingTask === task.id}
            onOpenHelp={openChat}
            onTaskCompleted={handleTaskCompleted}
          />
        ))}

      {!dayCompleted && tasks.length === 0 && (
        <div className="goal-card">
          <strong>No tasks unlocked right now.</strong>
          <div className="task-submeta">
            Approve a goal or unlock the next day to keep momentum going.
          </div>
        </div>
      )}

      {activeTask && (
        <TaskFocusChat
          activeTaskId={activeTask.id}
          taskTitle={activeTask.title}
          hasStructuredInput={activeTask.requires_input}
          messages={messages}
          setMessages={setMessages}
          onClose={() => {
            setActiveTaskId(null);
            setMessages([]);
          }}
        />
      )}
    </div>
  );
}

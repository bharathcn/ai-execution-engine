"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiFetch } from "../lib/api";

export default function GoalForm({ onGoalActivated }: any) {
  const [goal, setGoal] = useState("");
  const [summary, setSummary] = useState("");
  const [goalId, setGoalId] = useState(null);
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [planTasks, setPlanTasks] = useState([]);
  const [planApproved, setPlanApproved] = useState(false);

  useEffect(() => {
    const goalFromUrl = searchParams.get("goal");

    if (goalFromUrl) {
      setGoalId(goalFromUrl);
    }
  }, []);

  async function submitGoal() {
    if (!goal || goal.trim() === "") {
      alert("Please enter a goal first");
      return;
    }

    setSummary("");
    setLoading(true);
    const response = await apiFetch("/goals/", {
      method: "POST",
      body: JSON.stringify({
        goal_text: goal,
      }),
    });

    const data = await response.json();
    console.log("Data:", data);
    setGoalId(data.goal_id);

    const parsedPlan = JSON.parse(data.plan);

    setSummary(parsedPlan.plan_summary);
    setPlanTasks(parsedPlan.tasks);
    setLoading(false);
    setGoal("");
  }

  return (
    <div style={{ marginTop: 40 }}>
      <h2>Create Goal</h2>

      <input
        value={goal}
        onChange={(e) => setGoal(e.target.value)}
        placeholder="Enter your goal"
        style={{
          padding: 10,
          width: 300,
          marginRight: 10,
        }}
      />

      <button onClick={submitGoal} disabled={loading}>
        {loading ? "Generating..." : "Generate Plan"}
      </button>

      {loading && (
        <div className="ai-overlay">
          <div className="ai-overlay-content">
            <div className="spinner"></div>
            <p>Generating AI plan...</p>
          </div>
        </div>
      )}

      <div style={{ marginTop: 30 }}>
        {summary && !planApproved && (
          <div style={{ marginTop: 30 }}>
            <h3>Plan Summary</h3>
            <p>{summary}</p>
          </div>
        )}
        {planTasks.length > 0 && !planApproved && (
          <div className="goal-card">
            <h3>Execution Plan</h3>

            {planTasks.map((task: any) => (
              <div key={task.day} style={{ marginBottom: "8px" }}>
                <strong>Day {task.day}</strong>: {task.title}
              </div>
            ))}

            <div style={{ marginTop: "15px", display: "flex", gap: "10px" }}>
              <button
                onClick={ async () => {
                  setPlanApproved(true);
                  setSummary("");
                  setPlanTasks([]);

                  await apiFetch(`/goals/${goalId}/activate`, {
                    method: "PATCH",
                  });

                  if (onGoalActivated) {
                    onGoalActivated();
                  }

                  const focusSection = document.getElementById("today");

                  if (focusSection) {
                    focusSection.scrollIntoView({ behavior: "smooth" });
                  }
                }}
              >
                Start Execution
              </button>

              <button
                style={{ background: "#e5e7eb", color: "#111" }}
                onClick={() => {
                  setSummary("");
                  setPlanTasks([]);
                  setPlanApproved(false);
                }}
              >
                Regenerate Plan
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

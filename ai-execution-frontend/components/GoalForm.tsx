"use client";

import { useState } from "react";
import { apiFetch } from "../lib/api";

type GoalQuestion = {
  key: string;
  question: string;
};

type GeneratedTask = {
  day_number: number;
  title: string;
};

export default function GoalForm({ onGoalActivated }: any) {
  const [step, setStep] = useState(1);
  const [goalText, setGoalText] = useState("");
  const [category, setCategory] = useState("");
  const [questions, setQuestions] = useState<GoalQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [generatedTasks, setGeneratedTasks] = useState<GeneratedTask[]>([]);
  const [goalId, setGoalId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingAction, setLoadingAction] = useState<
    "questions" | "generate" | "approve" | "regenerate" | null
  >(null);
  const [error, setError] = useState("");

  function resetForm() {
    setStep(1);
    setGoalText("");
    setCategory("");
    setQuestions([]);
    setAnswers({});
    setGeneratedTasks([]);
    setGoalId(null);
    setLoadingAction(null);
    setError("");
  }

  async function getErrorMessage(response: Response) {
    try {
      const data = await response.json();
      return data.detail || "Something went wrong. Please try again.";
    } catch {
      return "Something went wrong. Please try again.";
    }
  }

  async function handleNext() {
    if (!goalText.trim()) {
      setError("Please enter a goal first");
      return;
    }

    setLoading(true);
    setLoadingAction("questions");
    setError("");

    try {
      const response = await apiFetch("/goals/intake/start", {
        method: "POST",
        body: JSON.stringify({
          goal_text: goalText,
        }),
      });

      if (!response.ok) {
        setError(await getErrorMessage(response));
        return;
      }

      const data = await response.json();

      setCategory(data.category || "");
      setQuestions(Array.isArray(data.questions) ? data.questions : []);
      setAnswers({});
      setStep(2);
    } catch {
      setError("Unable to start goal intake. Please try again.");
    } finally {
      setLoading(false);
      setLoadingAction(null);
    }
  }

  async function handleGeneratePlan() {
    setLoading(true);
    setLoadingAction("generate");
    setError("");

    try {
      const response = await apiFetch("/goals/intake/complete", {
        method: "POST",
        body: JSON.stringify({
          goal_text: goalText,
          category,
          answers,
        }),
      });

      if (!response.ok) {
        setError(await getErrorMessage(response));
        return;
      }

      const data = await response.json();

      setGeneratedTasks(Array.isArray(data.tasks) ? data.tasks : []);
      setGoalId(typeof data.goal_id === "number" ? data.goal_id : null);
      setStep(3);
    } catch {
      setError("Unable to generate plan. Please try again.");
    } finally {
      setLoading(false);
      setLoadingAction(null);
    }
  }

  async function handleApprovePlan() {
    if (!goalId) {
      setError("Unable to approve this plan. Please generate it again.");
      return;
    }

    setLoading(true);
    setLoadingAction("approve");
    setError("");

    try {
      const response = await apiFetch(`/goals/${goalId}/approve`, {
        method: "POST",
      });

      if (!response.ok) {
        setError(await getErrorMessage(response));
        return;
      }

      resetForm();

      if (onGoalActivated) {
        onGoalActivated();
      }
    } catch {
      setError("Unable to approve plan. Please try again.");
    } finally {
      setLoading(false);
      setLoadingAction(null);
    }
  }

  async function handleRegeneratePlan() {
    if (!goalId) {
      setError("Unable to regenerate this plan. Please start again.");
      return;
    }

    setLoading(true);
    setLoadingAction("regenerate");
    setError("");

    try {
      const response = await apiFetch(`/goals/${goalId}/regenerate`, {
        method: "POST",
      });

      if (!response.ok) {
        setError(await getErrorMessage(response));
        return;
      }

      const data = await response.json();

      setGeneratedTasks(Array.isArray(data.tasks) ? data.tasks : []);
      setGoalId(typeof data.goal_id === "number" ? data.goal_id : goalId);
    } catch {
      setError("Unable to regenerate plan. Please try again.");
    } finally {
      setLoading(false);
      setLoadingAction(null);
    }
  }

  const loadingMessage =
    loadingAction === "questions"
      ? "Loading questions..."
      : loadingAction === "generate"
        ? "Generating plan..."
        : loadingAction === "approve"
          ? "Approving plan..."
          : "Regenerating plan...";

  return (
    <div className="goal-form">
      <h2>Create Goal</h2>

      {step === 1 && (
        <div className="goal-input-row">
          <input
            value={goalText}
            onChange={(e) => setGoalText(e.target.value)}
            placeholder="Enter your goal"
          />

          <button onClick={handleNext} disabled={loading}>
            {loading ? "Loading..." : "Next"}
          </button>
        </div>
      )}

      {step === 2 && (
        <div className="goal-card goal-flow-card">
          <div className="goal-summary">
            <strong>Goal:</strong> {goalText}
          </div>

          {category && (
            <div className="goal-category">
              Category: {category}
            </div>
          )}

          {questions.map((q) => (
            <div key={q.key} className="form-field">
              <label htmlFor={q.key} className="form-label">
                {q.question}
              </label>
              <input
                id={q.key}
                type="text"
                value={answers[q.key] || ""}
                onChange={(e) =>
                  setAnswers((prev) => ({
                    ...prev,
                    [q.key]: e.target.value,
                  }))
                }
              />
            </div>
          ))}

          <div className="action-row">
            <button onClick={handleGeneratePlan} disabled={loading}>
              {loading ? "Generating..." : "Generate Plan"}
            </button>

            <button
              type="button"
              className="button-secondary"
              onClick={() => {
                setStep(1);
                setError("");
              }}
              disabled={loading}
            >
              Back
            </button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="goal-card goal-flow-card">
          <div className="goal-summary">
            <strong>Goal:</strong> {goalText}
          </div>

          <div className="goal-summary">
            <strong>Review Tasks</strong>
          </div>

          <div className="generated-task-list">
            {generatedTasks.map((task) => (
              <div
                key={`${task.day_number}-${task.title}`}
                className="generated-task-card"
              >
                <strong>Day {task.day_number}</strong>
                <p>{task.title}</p>
              </div>
            ))}
          </div>

          <div className="action-row">
            <button onClick={handleApprovePlan} disabled={loading || !goalId}>
              {loadingAction === "approve" ? "Approving..." : "Approve Plan"}
            </button>

            <button
              type="button"
              className="button-secondary"
              onClick={handleRegeneratePlan}
              disabled={loading || !goalId}
            >
              {loadingAction === "regenerate"
                ? "Regenerating..."
                : "Regenerate Plan"}
            </button>
          </div>
        </div>
      )}

      {error && <p className="error-text">{error}</p>}

      {loading && (
        <div className="ai-overlay">
          <div className="ai-overlay-content">
            <div className="spinner"></div>
            <p>{loadingMessage}</p>
          </div>
        </div>
      )}
    </div>
  );
}

"use client";
import { useState } from "react";
import GoalForm from "../components/GoalForm";
import GoalsList from "../components/GoalsList";
import TodayTasks from "../components/TodayTasks";

export default function Home() {
  const [todayRefreshTrigger, setTodayRefreshTrigger] = useState(0);
  const [goalsRefreshTrigger, setGoalsRefreshTrigger] = useState(0);

  const handleGoalActivated = () => {
    setTodayRefreshTrigger((prev) => prev + 1);
    setGoalsRefreshTrigger((prev) => prev + 1);
  };

  const handleTaskCompleted = () => {
    setGoalsRefreshTrigger((prev) => prev + 1);
  };

  return (
    <div className="container">
      <h1>AI Execution Engine</h1>

      <div className="dashboard">
        <div className="sidebar">
          <div
            className="sidebar-item"
            onClick={() =>
              document.getElementById("today")?.scrollIntoView({ behavior: "smooth" })
            }
          >
            Today's Focus
          </div>
          <div
            className="sidebar-item"
            onClick={() =>
              document.getElementById("create")?.scrollIntoView({ behavior: "smooth" })
            }
          >
            Create Goal
          </div>
          <div
            className="sidebar-item"
            onClick={() =>
              document.getElementById("goals")?.scrollIntoView({ behavior: "smooth" })
            }
          >
            Your Goals
          </div>
        </div>

        <div>
          <div id="today" className="section">
            <TodayTasks
              refreshTrigger={todayRefreshTrigger}
              onTaskComplete={handleTaskCompleted}
            />
          </div>

          <div id="create" className="section">
            <GoalForm onGoalActivated={handleGoalActivated} />
          </div>

          <div id="goals" className="section">
            <GoalsList refreshTrigger={goalsRefreshTrigger} />
          </div>
        </div>
      </div>
    </div>
  );
}

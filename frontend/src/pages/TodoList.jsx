// TodoList.jsx — Stage 5
// Paper: "Personalized to-do checklists specifying concrete actions.
//         Priority ranking, time estimates, difficulty levels.
//         Progress tracking — mark completed items."

import { useState } from "react";
import { useApp }   from "../context/AppContext";
import "./pages.css";

const CATEGORY_ICONS = {
  resume:            "📄",
  interview:         "🎤",
  skill_development: "💡",
};

const PRIORITY_COLORS = {
  high:   "#ef4444",
  medium: "#f59e0b",
  low:    "#10b981",
};

export default function TodoList() {
  const { todoList, selectedRole, resetAll } = useApp();
  const [todos, setTodos] = useState(
    todoList.map((t, i) => ({ ...t, id: i, done: false }))
  );
  const [filter, setFilter] = useState("all");

  const toggleDone = (id) => {
    setTodos(todos.map((t) => t.id === id ? { ...t, done: !t.done } : t));
  };

  const filtered = filter === "all"
    ? todos
    : filter === "done"
    ? todos.filter((t) => t.done)
    : todos.filter((t) => t.category === filter && !t.done);

  const doneCount = todos.filter((t) => t.done).length;
  const progress  = Math.round((doneCount / todos.length) * 100) || 0;

  return (
    <div className="stage-container wide">
      <div className="stage-header">
        <span className="stage-badge">Stage 5 of 5</span>
        <h1>Your Personalized Action Plan</h1>
        <p>Complete these tasks to strengthen your profile for <strong>{selectedRole}</strong>.</p>
      </div>

      {/* Progress — paper: "progress tracking" */}
      <div className="card todo-progress-card">
        <div className="todo-progress-header">
          <span>{doneCount} of {todos.length} tasks completed</span>
          <span>{progress}%</span>
        </div>
        <div className="progress-bar">
          <div className="progress-fill green" style={{ width: `${progress}%` }} />
        </div>
      </div>

      {/* Filter tabs */}
      <div className="filter-tabs">
        {["all", "resume", "interview", "skill_development", "done"].map((f) => (
          <button
            key={f}
            className={`filter-tab ${filter === f ? "active" : ""}`}
            onClick={() => setFilter(f)}
          >
            {f === "skill_development" ? "Skills" : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {/* Todo Items — paper: priority, time estimate, difficulty */}
      <div className="todo-list">
        {filtered.map((todo) => (
          <div
            key={todo.id}
            className={`todo-item ${todo.done ? "done" : ""}`}
            onClick={() => toggleDone(todo.id)}
          >
            <div className="todo-checkbox">
              {todo.done ? "✅" : "⬜"}
            </div>
            <div className="todo-content">
              <div className="todo-task">{todo.task}</div>
              <div className="todo-meta">
                <span className="todo-category">
                  {CATEGORY_ICONS[todo.category]} {todo.category?.replace("_", " ")}
                </span>
                <span
                  className="todo-priority"
                  style={{ color: PRIORITY_COLORS[todo.priority] }}
                >
                  ● {todo.priority} priority
                </span>
                <span className="todo-time">
                  ⏱ {todo.estimated_hours}h
                </span>
                <span className="todo-difficulty">
                  {todo.difficulty === "easy"   ? "🟢" :
                   todo.difficulty === "medium" ? "🟡" : "🔴"} {todo.difficulty}
                </span>
              </div>
              {todo.resource_url && (
                <a
                  href={todo.resource_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="todo-resource"
                  onClick={(e) => e.stopPropagation()}
                >
                  📚 {todo.resource_note || "View Resource"}
                </a>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Restart */}
      <div className="todo-actions">
        <button className="btn-secondary" onClick={resetAll}>
          Start New Analysis
        </button>
      </div>
    </div>
  );
}
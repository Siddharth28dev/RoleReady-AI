// StageBar.jsx
// Paper: "5 distinct stages that guide candidates through career preparation"

import { useApp } from "../context/AppContext";
import "./StageBar.css";

const STAGES = [
  { num: 1, label: "Resume Upload" },
  { num: 2, label: "Role Selection" },
  { num: 3, label: "AI Interview" },
  { num: 4, label: "Feedback" },
  { num: 5, label: "To-Do List" },
];

export default function StageBar() {
  const { currentStage } = useApp();
  return (
    <div className="stagebar">
      {STAGES.map((s, i) => (
        <div key={s.num} className="stagebar__item">
          <div className={`stagebar__circle ${
            currentStage > s.num  ? "done" :
            currentStage === s.num ? "active" : ""
          }`}>
            {currentStage > s.num ? "✓" : s.num}
          </div>
          <span className={`stagebar__label ${currentStage === s.num ? "active" : ""}`}>
            {s.label}
          </span>
          {i < STAGES.length - 1 && (
            <div className={`stagebar__line ${currentStage > s.num ? "done" : ""}`} />
          )}
        </div>
      ))}
    </div>
  );
}
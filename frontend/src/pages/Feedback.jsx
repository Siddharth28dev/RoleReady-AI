// Feedback.jsx — Stage 4
// Paper: "Comprehensive feedback covering resume quality,
//         interview performance, and identified skill gaps.
//         Scores presented with explanatory context."

import { useState, useEffect } from "react";
import { useApp } from "../context/AppContext";
import { generateFeedback, getTransparencyReport } from "../api/axiosClient";
import "./pages.css";

export default function Feedback() {
  const {
    resumeData, skillGapData, interviewData, sessionId,
    selectedRole, setFeedbackData, setTodoList, setCurrentStage,
  } = useApp();

  const [feedback,     setFeedback]     = useState(null);
  const [transparency, setTransparency] = useState(null);
  const [loading,      setLoading]      = useState(true);
  const [error,        setError]        = useState("");

  useEffect(() => {
    (async () => {
      try {
        const res = await generateFeedback({
          resume_data:    resumeData,
          skill_gap_data: skillGapData,
          interview_data: interviewData,
          job_role:       selectedRole,
          session_id:     sessionId,
        });
        if (res.data.success) {
          setFeedback(res.data.feedback);
          setFeedbackData(res.data.feedback);
          setTodoList(res.data.todo_list || []);

          // Paper: transparency report
          const fb = res.data.feedback;
          const tr = await getTransparencyReport({
            resume_score:    fb.resume_section?.score    || 0,
            skill_score:     fb.skill_section?.score     || 0,
            interview_score: fb.interview_section?.score || 0,
            overall_score:   fb.overall?.score           || 0,
          });
          setTransparency(tr.data.report);
        } else {
          setError(res.data.error || "Feedback generation failed.");
        }
      } catch (e) {
        setError("Server error generating feedback.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <div className="stage-container"><div className="loading">Generating your personalized feedback report...</div></div>;
  if (error)   return <div className="stage-container"><div className="error-msg">⚠️ {error}</div></div>;

  const overall = feedback?.overall;

  return (
    <div className="stage-container wide">
      <div className="stage-header">
        <span className="stage-badge">Stage 4 of 5</span>
        <h1>Your Feedback Report</h1>
        <p>{feedback?.summary}</p>
      </div>

      {/* Overall Score */}
      <div className="card score-card">
        <div className="overall-score">
          <div className="score-circle" style={{
            background: `conic-gradient(#4f46e5 ${overall?.score * 3.6}deg, #e5e7eb 0deg)`
          }}>
            <span>{overall?.score}%</span>
          </div>
          <div>
            <h2>Overall Score: {overall?.rating}</h2>
            <div className="component-scores">
              <ScoreRow label="Resume Quality"       score={feedback?.resume_section?.score}    weight="25%" />
              <ScoreRow label="Skill Match"          score={feedback?.skill_section?.score}     weight="35%" />
              <ScoreRow label="Interview Performance" score={feedback?.interview_section?.score} weight="40%" />
            </div>
          </div>
        </div>
      </div>

      {/* 3 Section Cards */}
      <div className="feedback-grid">
        <FeedbackSection
          title="📄 Resume Quality"
          score={feedback?.resume_section?.score}
          rating={feedback?.resume_section?.rating}
          strengths={feedback?.resume_section?.strengths}
          weaknesses={feedback?.resume_section?.weaknesses}
        />
        <FeedbackSection
          title="🎯 Skill Gap Analysis"
          score={feedback?.skill_section?.score}
          rating={feedback?.skill_section?.rating}
          strengths={feedback?.skill_section?.strengths}
          weaknesses={feedback?.skill_section?.weaknesses}
          extra={
            <div className="gap-info">
              <span className="core-gap">🔴 Core gaps: {feedback?.skill_section?.core_gaps?.length || 0}</span>
              <span className="pref-gap">🟡 Preferred gaps: {feedback?.skill_section?.preferred_gaps?.length || 0}</span>
            </div>
          }
        />
        <FeedbackSection
          title="🎤 Interview Performance"
          score={feedback?.interview_section?.score}
          rating={feedback?.interview_section?.rating}
          strengths={feedback?.interview_section?.strengths}
          weaknesses={feedback?.interview_section?.weaknesses}
          extra={
            feedback?.interview_section?.breakdown && (
              <div className="breakdown">
                {Object.entries(feedback.interview_section.breakdown).map(([k, v]) => (
                  <span key={k} className={`breakdown-badge ${k}`}>{k}: {v}</span>
                ))}
              </div>
            )
          }
        />
      </div>

      {/* Transparency — Paper: "explain how AI reaches conclusions" */}
      {transparency && (
        <div className="card transparency-card">
          <h3>🔍 {transparency.title}</h3>
          <p>{transparency.explanation}</p>
          <div className="ai-methods">
            <strong>AI Methods Used:</strong>
            <ul>{transparency.ai_methods_used?.map((m, i) => <li key={i}>{m}</li>)}</ul>
          </div>
          <p className="transparency-note">{transparency.transparency_note}</p>
        </div>
      )}

      <button className="btn-primary" onClick={() => setCurrentStage(5)}>
        View Your To-Do List →
      </button>
    </div>
  );
}

function ScoreRow({ label, score, weight }) {
  return (
    <div className="score-row">
      <span>{label} ({weight})</span>
      <div className="score-bar">
        <div className="score-fill" style={{ width: `${score || 0}%` }} />
      </div>
      <span className="score-num">{score || 0}%</span>
    </div>
  );
}

function FeedbackSection({ title, score, rating, strengths, weaknesses, extra }) {
  return (
    <div className="card section-card">
      <div className="section-header">
        <h3>{title}</h3>
        <span className="section-score">{score}% — {rating}</span>
      </div>
      {extra}
      {strengths?.length > 0 && (
        <div className="strengths">
          <h4>✅ Strengths</h4>
          <ul>{strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      )}
      {weaknesses?.length > 0 && (
        <div className="weaknesses">
          <h4>❌ Improve</h4>
          <ul>{weaknesses.map((w, i) => <li key={i}>{w}</li>)}</ul>
        </div>
      )}
    </div>
  );
}
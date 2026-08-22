// Interview.jsx — Stage 3
// Fixed: stale closure bug, question 13 of 12 bug, submit not working

import { useState, useEffect, useRef, useCallback } from "react";
import { useApp } from "../context/AppContext";
import { generateQuestions, evaluateAllAnswers } from "../api/axiosClient";
import "./pages.css";

const TIME_LIMIT = 120;

export default function Interview() {
  const {
    resumeData, resumeId, selectedRole, skillGapData, sessionId,
    setQuestions, setAnswers, setInterviewData, setSessionId, setCurrentStage,
  } = useApp();

  const [questions,   setLocalQuestions] = useState([]);
  const [currentIdx,  setCurrentIdx]     = useState(0);
  const [currentAns,  setCurrentAns]     = useState("");
  const [timeLeft,    setTimeLeft]       = useState(TIME_LIMIT);
  const [loading,     setLoading]        = useState(true);
  const [submitting,  setSubmitting]     = useState(false);
  const [error,       setError]          = useState("");

  // Refs to avoid stale closures in timer callback
  const timerRef    = useRef(null);
  const calledRef   = useRef(false);
  const answersRef  = useRef([]);      // always up to date
  const idxRef      = useRef(0);       // always up to date
  const questionsRef = useRef([]);     // always up to date

  // Keep refs in sync
  useEffect(() => { idxRef.current = currentIdx; }, [currentIdx]);
  useEffect(() => { questionsRef.current = questions; }, [questions]);

  // Flatten { technical:[..], problem_solving:[..], ... } → flat array
  const flattenQuestions = (data) => {
    const flat = [];
    const obj  = data?.data?.questions || data?.questions || {};
    for (const type of ["technical", "problem_solving", "behavioral", "situational"]) {
      for (const item of (obj[type] || [])) {
        flat.push({
          id:         item.id        || null,
          question:   item.question   || "",
          type:       item.type       || type,
          skill:      item.skill      || "",
          difficulty: item.difficulty || "",
          is_gap:     item.is_gap     || false,
        });
      }
    }
    return flat;
  };

  // Submit all answers to evaluation API
  const submitAll = useCallback(async (allAnswers) => {
    setSubmitting(true);
    try {
      const res = await evaluateAllAnswers({ answers: allAnswers, session_id: sessionId });
      if (res.data) {
        setAnswers(allAnswers);
        setInterviewData(res.data);
        setCurrentStage(4);
      } else {
        setError("Evaluation returned no data.");
        setSubmitting(false);
      }
    } catch (e) {
      setError("Evaluation failed: " + (e?.response?.data?.error || e.message));
      setSubmitting(false);
    }
  }, [setAnswers, setInterviewData, setCurrentStage, sessionId]);

  // Move to next question or submit — uses refs to avoid stale state
  const handleNext = useCallback((timedOut = false) => {
    clearInterval(timerRef.current);

    const qs  = questionsRef.current;
    const idx = idxRef.current;
    const ans = (timedOut && !currentAns) ? "[No answer — timed out]" : currentAns;

    // Build new answer entry
    const newAnswer = {
      question_id:      qs[idx]?.id     || null,
      question:         qs[idx]?.question || "",
      candidate_answer: ans,
      question_type:    qs[idx]?.type     || "technical",
      skill:            qs[idx]?.skill    || "",
      job_role:         selectedRole      || "",
    };

    const updatedAnswers = [...answersRef.current, newAnswer];
    answersRef.current   = updatedAnswers;

    const nextIdx = idx + 1;

    if (nextIdx < qs.length) {
      // More questions remain
      setCurrentIdx(nextIdx);
      setCurrentAns("");
      setTimeLeft(TIME_LIMIT);
      // Start timer for next question
      timerRef.current = setInterval(() => {
        setTimeLeft((t) => {
          if (t <= 1) {
            clearInterval(timerRef.current);
            handleNext(true);
            return 0;
          }
          return t - 1;
        });
      }, 1000);
    } else {
      // All questions answered — submit
      submitAll(updatedAnswers);
    }
  }, [currentAns, selectedRole, submitAll]);

  // Timer start helper
  const startTimer = useCallback(() => {
    clearInterval(timerRef.current);
    setTimeLeft(TIME_LIMIT);
    timerRef.current = setInterval(() => {
      setTimeLeft((t) => {
        if (t <= 1) {
          clearInterval(timerRef.current);
          handleNext(true);
          return 0;
        }
        return t - 1;
      });
    }, 1000);
  }, [handleNext]);

  // Generate questions on mount — once only
  useEffect(() => {
    if (calledRef.current) return;
    calledRef.current = true;

    (async () => {
      try {
        const res = await generateQuestions({
          job_role:           selectedRole            || "Software Developer",
          resume_text:        resumeData?.parsed_text || "",
          resume_id:          resumeId,
          skill_gaps:         skillGapData?.missing_skills  || [],
          matched_skills:     skillGapData?.matched_skills  || [],
          experience_level:   resumeData?.experience?.level || "fresher",
          questions_per_type: 3,
        });

        if (res.data?.success) {
          const flat = flattenQuestions(res.data);
          if (flat.length === 0) {
            setError("No questions generated. Please go back and try again.");
            return;
          }
          questionsRef.current = flat;
          setLocalQuestions(flat);
          setQuestions(flat);
          setSessionId(res.data?.data?.session_id || null);
          startTimer();
        } else {
          setError(res.data?.error || "Failed to generate questions.");
        }
      } catch (e) {
        setError("Server error: " + (e?.response?.data?.error || e.message));
      } finally {
        setLoading(false);
      }
    })();

    return () => clearInterval(timerRef.current);
  }, []);

  const timerColor = timeLeft > 60 ? "#10b981" : timeLeft > 30 ? "#f59e0b" : "#ef4444";
  const safeIdx    = Math.min(currentIdx, questions.length - 1);
  const progress   = questions.length > 0
    ? ((safeIdx) / questions.length) * 100
    : 0;
  const q = questions[safeIdx];

  if (loading)    return <div className="stage-container"><div className="loading">⏳ Generating your personalized interview questions...</div></div>;
  if (submitting) return <div className="stage-container"><div className="loading">🧠 Evaluating your answers with AI... Please wait.</div></div>;
  if (error)      return <div className="stage-container"><div className="error-msg">⚠️ {error}</div></div>;
  if (!q)         return <div className="stage-container"><div className="loading">Loading question...</div></div>;

  const isLast    = currentIdx === questions.length - 1;
  const btnLabel  = isLast ? "Submit Interview →" : "Next Question →";

  return (
    <div className="stage-container">
      <div className="stage-header">
        <span className="stage-badge">Stage 3 of 5</span>
        <h1>AI Interview Simulation</h1>
        <p>Answer each question within the time limit. Be specific and structured.</p>
      </div>

      {/* Progress bar */}
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>
      <div className="progress-label">
        Question {currentIdx + 1} of {questions.length}
      </div>

      <div className="card">
        {/* Timer */}
        <div className="timer" style={{ color: timerColor }}>
          ⏱ {Math.floor(timeLeft / 60)}:{String(timeLeft % 60).padStart(2, "0")}
          <span className="timer-label"> remaining</span>
        </div>

        {/* Question meta badges */}
        <div className="question-meta">
          <span className={`type-badge type-${q.type}`}>
            {q.type?.replace("_", " ")}
          </span>
          {q.skill      && <span className="skill-badge">{q.skill}</span>}
          {q.difficulty && <span className="diff-badge">{q.difficulty}</span>}
          {q.is_gap     && (
            <span className="diff-badge" style={{ background: "#fef9c3", color: "#854d0e" }}>
              skill gap
            </span>
          )}
        </div>

        {/* Question text */}
        <div className="question-text">{q.question}</div>

        {/* STAR hint for behavioral */}
        {q.type === "behavioral" && (
          <div style={{
            background: "#f0f9ff", padding: "8px 12px", borderRadius: "6px",
            fontSize: "12px", color: "#0369a1", marginBottom: "12px",
          }}>
            💡 Use STAR format: <strong>S</strong>ituation →{" "}
            <strong>T</strong>ask → <strong>A</strong>ction →{" "}
            <strong>R</strong>esult
          </div>
        )}

        {/* Answer textarea */}
        <textarea
          className="textarea answer-input"
          rows={6}
          placeholder="Type your answer here... Be specific with examples."
          value={currentAns}
          onChange={(e) => setCurrentAns(e.target.value)}
        />
        <small>{currentAns.split(" ").filter(Boolean).length} words</small>

        {/* Next / Submit button */}
        <button
          className="btn-primary"
          onClick={() => handleNext(false)}
          disabled={!currentAns.trim()}
          style={{ marginTop: "16px", opacity: currentAns.trim() ? 1 : 0.5 }}
        >
          {btnLabel}
        </button>
      </div>
    </div>
  );
}
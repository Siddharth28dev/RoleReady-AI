// AppContext.jsx
// Paper: "5-stage workflow — state flows through all stages"
// Global state for entire workflow

import { createContext, useContext, useState } from "react";

const AppContext = createContext(null);

export function AppProvider({ children }) {
  // ── Auth ──────────────────────────────────────────────────────────────
  // Hydrated from localStorage on first load so a page refresh doesn't
  // force a re-login. The token itself is what the axios interceptor
  // attaches to every request (see api/axiosClient.js).
  const [token, setToken] = useState(() => localStorage.getItem("auth_token"));
  const [user,  setUser]  = useState(() => {
    const raw = localStorage.getItem("auth_user");
    return raw ? JSON.parse(raw) : null;
  });

  const login = (newToken, newUser) => {
    localStorage.setItem("auth_token", newToken);
    localStorage.setItem("auth_user", JSON.stringify(newUser));
    setToken(newToken);
    setUser(newUser);
  };

  const logout = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    setToken(null);
    setUser(null);
    resetAll();
  };

  // Stage tracking — paper: "5 distinct stages"
  const [currentStage, setCurrentStage] = useState(1);

  // Stage 1 — Resume data
  const [resumeData,   setResumeData]   = useState(null);
  const [resumeFile,   setResumeFile]   = useState(null);
  const [resumeId,     setResumeId]     = useState(null); // DB id — now that uploads persist

  // Stage 2 — Role + JD
  const [selectedRole, setSelectedRole] = useState("");
  const [jdText,       setJdText]       = useState("");
  const [skillGapData, setSkillGapData] = useState(null);

  // Stage 3 — Interview
  const [questions,    setQuestions]    = useState([]);
  const [answers,      setAnswers]      = useState([]);
  const [interviewData, setInterviewData] = useState(null);
  const [sessionId,    setSessionId]    = useState(null); // DB id — now that sessions persist

  // Stage 4 & 5 — Feedback + Todo
  const [feedbackData, setFeedbackData] = useState(null);
  const [todoList,     setTodoList]     = useState([]);

  const resetAll = () => {
    setCurrentStage(1);
    setResumeData(null);   setResumeFile(null);   setResumeId(null);
    setSelectedRole("");   setJdText("");         setSkillGapData(null);
    setQuestions([]);      setAnswers([]);        setInterviewData(null); setSessionId(null);
    setFeedbackData(null); setTodoList([]);
  };

  return (
    <AppContext.Provider value={{
      token, user, login, logout,
      currentStage, setCurrentStage,
      resumeData,   setResumeData,
      resumeFile,   setResumeFile,
      resumeId,     setResumeId,
      selectedRole, setSelectedRole,
      jdText,       setJdText,
      skillGapData, setSkillGapData,
      questions,    setQuestions,
      answers,      setAnswers,
      interviewData, setInterviewData,
      sessionId,    setSessionId,
      feedbackData, setFeedbackData,
      todoList,     setTodoList,
      resetAll,
    }}>
      {children}
    </AppContext.Provider>
  );
}

export const useApp = () => useContext(AppContext);
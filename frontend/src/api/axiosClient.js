// axiosClient.js
// Paper: "API-based communication between modules"
// All backend API calls go through this single client

import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:5000/api";

const axiosClient = axios.create({
  baseURL: API_BASE,
  timeout: 60000, // 60s — fine for most calls (uploads, skill-gap, feedback)
  headers: { "Content-Type": "application/json" },
});

// Attach the JWT (if we have one) to every outgoing request. This is what
// was missing entirely before — the backend now requires a token on
// resume/interview/feedback routes, and this is the only place it gets
// attached, so every page just calls the exported functions below and
// doesn't need to think about auth headers itself.
axiosClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("auth_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// If the token is missing/expired, the backend returns 401 — bounce back
// to login instead of leaving the user stuck on a silently-failing page.
axiosClient.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err?.response?.status === 401) {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("auth_user");
      // No router in this app — a full reload re-mounts App, which reads
      // localStorage on mount and falls back to the login screen itself.
      window.location.reload();
    }
    return Promise.reject(err);
  }
);

// AI-generation-heavy calls (question generation, answer evaluation) run
// FLAN-T5 on CPU. Cold-start (first call after server start/reload) has to
// load the base model + LoRA adapter into memory before it can generate
// anything, which alone can take well over 60s — separate from the actual
// generation time for N questions. Give these calls more room; the 60s
// default stays for everything else so real connectivity failures still
// surface quickly instead of hanging for 3 minutes.
const AI_GENERATION_TIMEOUT_MS = 180000; // 3 min

// ── Auth APIs ─────────────────────────────────────────────────────────────────
export const registerUser = (data) =>
  axiosClient.post("/auth/register", data);

export const loginUser = (data) =>
  axiosClient.post("/auth/login", data);

export const getCurrentUser = () =>
  axiosClient.get("/auth/me");

// ── Resume APIs ───────────────────────────────────────────────────────────────
export const uploadResume = (formData) =>
  axiosClient.post("/resume/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

// ── Analysis APIs ─────────────────────────────────────────────────────────────
export const analyzeSkillGap = (data) =>
  axiosClient.post("/analysis/skill-gap", data);

// ── Interview APIs ────────────────────────────────────────────────────────────
export const generateQuestions = (data) =>
  axiosClient.post("/interview/generate-questions", data, {
    timeout: AI_GENERATION_TIMEOUT_MS,
  });

export const evaluateAllAnswers = (data) =>
  axiosClient.post("/interview/evaluate-all", data, {
    timeout: AI_GENERATION_TIMEOUT_MS,
  });

// ── Feedback APIs ─────────────────────────────────────────────────────────────
export const generateFeedback = (data) =>
  axiosClient.post("/feedback/generate", data);

export const generateTodo = (data) =>
  axiosClient.post("/feedback/todo", data);

// Deletes whichever account the JWT belongs to — the backend no longer
// trusts a user_id passed here (that used to let anyone delete anyone
// else's account by guessing an ID).
export const deleteAccount = () =>
  axiosClient.delete("/feedback/delete-account");

// ── Bias APIs ─────────────────────────────────────────────────────────────────
export const auditJD = (jdText) =>
  axiosClient.post("/bias/audit-jd", { jd_text: jdText });

export const getTransparencyReport = (scores) =>
  axiosClient.post("/bias/transparency", scores);

export default axiosClient;
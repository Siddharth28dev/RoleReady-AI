// RoleSelection.jsx — Stage 2
// Paper: "Users select their desired job role from a categorized database.
//         System displays role requirements and expected competencies."
// Paper: "Skill matching employs semantic similarity scoring."

import { useState } from "react";
import { useApp }   from "../context/AppContext";
import { analyzeSkillGap, auditJD } from "../api/axiosClient";
import "./pages.css";

const COMMON_ROLES = [
  "Software Engineer", "Data Scientist", "Machine Learning Engineer",
  "Frontend Developer", "Backend Developer", "Full Stack Developer",
  "DevOps Engineer", "Data Analyst", "Product Manager",
  "Cybersecurity Analyst", "Cloud Architect", "Mobile Developer",
];

export default function RoleSelection() {
  const {
    resumeData, setSelectedRole, setJdText,
    setSkillGapData, setCurrentStage,
  } = useApp();

  const [role,    setRole]    = useState("");
  const [jd,     setJd]      = useState("");
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState("");
  const [biasWarn, setBiasWarn] = useState([]);

  const handleJdChange = async (text) => {
    setJd(text);
    // Paper: bias audit on JD
    if (text.length > 100) {
      try {
        const res = await auditJD(text);
        if (res.data.audit?.flags?.length > 0) {
          setBiasWarn(res.data.audit.flags);
        } else {
          setBiasWarn([]);
        }
      } catch (_) {}
    }
  };

  const handleAnalyze = async () => {
    if (!role)          { setError("Please select or enter a job role."); return; }
    if (jd.length < 50) { setError("Please enter a job description (min 50 characters)."); return; }

    setLoading(true);
    setError("");

    try {
      const res = await analyzeSkillGap({
        jd_text:          jd,
        resume_text:      resumeData?.parsed_text || "",
        resume_skills:    resumeData?.skills?.all_skills || [],
        experience_level: resumeData?.experience?.level,
      });

      if (res.data.success) {
        setSelectedRole(role);
        setJdText(jd);
        setSkillGapData(res.data.analysis);
        setCurrentStage(3);
      } else {
        setError(res.data.error || "Analysis failed.");
      }
    } catch (e) {
      setError("Server error during skill analysis.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="stage-container">
      <div className="stage-header">
        <span className="stage-badge">Stage 2 of 5</span>
        <h1>Select Target Role</h1>
        <p>Choose your desired job role and paste the job description for AI analysis.</p>
      </div>

      <div className="card">
        {/* Role Selection */}
        <div className="form-group">
          <label>Job Role</label>
          <input
            type="text"
            className="input"
            placeholder="e.g. Software Engineer"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            list="roles-list"
          />
          <datalist id="roles-list">
            {COMMON_ROLES.map((r) => <option key={r} value={r} />)}
          </datalist>
        </div>

        {/* JD Input */}
        <div className="form-group">
          <label>Job Description</label>
          <textarea
            className="textarea"
            rows={8}
            placeholder="Paste the full job description here..."
            value={jd}
            onChange={(e) => handleJdChange(e.target.value)}
          />
          <small>{jd.length} characters</small>
        </div>

        {/* Bias Warning — Paper: bias audit on JD */}
        {biasWarn.length > 0 && (
          <div className="bias-warn">
            <strong>⚠️ Bias detected in JD:</strong>
            <ul>{biasWarn.map((f, i) => <li key={i}>{f}</li>)}</ul>
          </div>
        )}

        {/* Resume Skills Preview */}
        {resumeData?.skills?.all_skills?.length > 0 && (
          <div className="skills-preview">
            <label>Your Detected Skills</label>
            <div className="skill-tags">
              {resumeData.skills.all_skills.slice(0, 10).map((s) => (
                <span key={s} className="skill-tag">{s}</span>
              ))}
              {resumeData.skills.all_skills.length > 10 && (
                <span className="skill-tag muted">
                  +{resumeData.skills.all_skills.length - 10} more
                </span>
              )}
            </div>
          </div>
        )}

        {error && <div className="error-msg">⚠️ {error}</div>}

        <button
          className="btn-primary"
          onClick={handleAnalyze}
          disabled={loading}
        >
          {loading ? "Analyzing Skills..." : "Analyze & Continue →"}
        </button>
      </div>
    </div>
  );
}
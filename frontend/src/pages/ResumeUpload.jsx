// ResumeUpload.jsx — Stage 1
// Paper: "Candidates upload resume in PDF, DOCX, or TXT format.
//         System performs initial parsing and validation,
//         providing immediate feedback on document quality."

import { useState } from "react";
import { useApp }   from "../context/AppContext";
import { uploadResume } from "../api/axiosClient";
import "./pages.css";

export default function ResumeUpload() {
  const { setResumeData, setResumeFile, setResumeId, setCurrentStage } = useApp();

  const [file,    setFile]    = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState("");
  const [drag,    setDrag]    = useState(false);

  const handleFile = (f) => {
    const allowed = ["application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "text/plain"];
    if (!allowed.includes(f.type)) {
      setError("Only PDF, DOCX, or TXT files are allowed.");
      return;
    }
    setFile(f);
    setError("");
  };

  const handleSubmit = async () => {
    if (!file) { setError("Please select a resume file."); return; }
    setLoading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await uploadResume(formData);
      if (res.data.success) {
        setResumeData(res.data);
        setResumeFile(file);
        setResumeId(res.data.resume_id || null);
        setCurrentStage(2);
      } else {
        setError(res.data.error || "Upload failed.");
      }
    } catch (e) {
      setError(e?.response?.data?.error || "Server error. Make sure backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="stage-container">
      <div className="stage-header">
        <span className="stage-badge">Stage 1 of 5</span>
        <h1>Upload Your Resume</h1>
        <p>Upload your resume and our AI will parse and analyze it instantly.</p>
      </div>

      <div className="card">
        <div
          className={`upload-zone ${drag ? "drag" : ""} ${file ? "has-file" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); handleFile(e.dataTransfer.files[0]); }}
          onClick={() => document.getElementById("resume-input").click()}
        >
          <input
            id="resume-input"
            type="file"
            accept=".pdf,.docx,.txt"
            style={{ display: "none" }}
            onChange={(e) => handleFile(e.target.files[0])}
          />
          {file ? (
            <div className="file-info">
              <span className="file-icon">📄</span>
              <span className="file-name">{file.name}</span>
              <span className="file-size">{(file.size / 1024).toFixed(1)} KB</span>
            </div>
          ) : (
            <div className="upload-prompt">
              <span className="upload-icon">⬆️</span>
              <p>Drag & drop your resume here</p>
              <span>or click to browse</span>
              <small>Supported: PDF, DOCX, TXT</small>
            </div>
          )}
        </div>

        {error && <div className="error-msg">⚠️ {error}</div>}

        <button
          className="btn-primary"
          onClick={handleSubmit}
          disabled={loading || !file}
        >
          {loading ? "Analyzing Resume..." : "Upload & Analyze →"}
        </button>
      </div>
    </div>
  );
}
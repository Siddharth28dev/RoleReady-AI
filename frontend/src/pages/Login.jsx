// Login.jsx
// New — no login screen existed before. Gates the whole 5-stage wizard,
// since every stage now persists to the DB against a real user_id.

import { useState } from "react";
import { useApp } from "../context/AppContext";
import { loginUser } from "../api/axiosClient";
import "./pages.css";

export default function Login({ onSwitchToRegister }) {
  const { login } = useApp();
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await loginUser({ email, password });
      if (res.data.success) {
        login(res.data.token, res.data.user);
      } else {
        setError(res.data.error || "Login failed.");
      }
    } catch (err) {
      setError(err?.response?.data?.error || "Server error during login.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="stage-container">
      <div className="stage-header">
        <h1>Log In</h1>
        <p>Sign in to continue your resume analysis and interview prep.</p>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              className="input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && <div className="error-msg">⚠️ {error}</div>}

          <button className="btn-primary" type="submit" disabled={loading}>
            {loading ? "Logging in..." : "Log In →"}
          </button>
        </form>

        <p style={{ marginTop: "16px", textAlign: "center" }}>
          Don't have an account?{" "}
          <button
            type="button"
            className="link-btn"
            onClick={onSwitchToRegister}
          >
            Register
          </button>
        </p>
      </div>
    </div>
  );
}
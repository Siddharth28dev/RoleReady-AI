// Register.jsx
// New — no signup screen existed before.

import { useState } from "react";
import { useApp } from "../context/AppContext";
import { registerUser } from "../api/axiosClient";
import "./pages.css";

export default function Register({ onSwitchToLogin }) {
  const { login } = useApp();
  const [name,     setName]     = useState("");
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    try {
      const res = await registerUser({ name, email, password });
      if (res.data.success) {
        login(res.data.token, res.data.user);
      } else {
        setError(res.data.error || "Registration failed.");
      }
    } catch (err) {
      setError(err?.response?.data?.error || "Server error during registration.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="stage-container">
      <div className="stage-header">
        <h1>Create Account</h1>
        <p>Sign up to save your resume analysis and interview progress.</p>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Name</label>
            <input
              type="text"
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

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
            <small>At least 8 characters.</small>
          </div>

          {error && <div className="error-msg">⚠️ {error}</div>}

          <button className="btn-primary" type="submit" disabled={loading}>
            {loading ? "Creating account..." : "Register →"}
          </button>
        </form>

        <p style={{ marginTop: "16px", textAlign: "center" }}>
          Already have an account?{" "}
          <button
            type="button"
            className="link-btn"
            onClick={onSwitchToLogin}
          >
            Log In
          </button>
        </p>
      </div>
    </div>
  );
}
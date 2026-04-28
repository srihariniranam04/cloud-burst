// frontend/src/Login.jsx
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";  // add useNavigate
import "./Login.css";

export default function Login({ onLoginSuccess }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");

    if (!username.trim() || !password.trim()) {
      setError("Username and password are required.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("/api/auth/login", {
        method:      "POST",
        headers:     { "Content-Type": "application/json" },
        credentials: "include",
        body:        JSON.stringify({ username: username.trim(), password }),
      });

      const data = await res.json();

      if (res.ok) {
        onLoginSuccess({ username: data.username, role: data.role });
        
      } else {
        setError(data.error || "Invalid credentials. Please try again.");
      }
    } catch (err) {
      setError("Cannot reach server. Make sure Flask is running on port 5000.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-bg">
      {/* Animated rain drops — matches your existing theme */}
      <div className="rain-container" aria-hidden="true">
        {Array.from({ length: 30 }).map((_, i) => (
          <div
            key={i}
            className="raindrop"
            style={{
              left:             `${Math.random() * 100}%`,
              animationDelay:   `${Math.random() * 3}s`,
              animationDuration:`${1.2 + Math.random() * 1.5}s`,
            }}
          />
        ))}
      </div>

      <div className="login-card">
        {/* Logo / title */}
        <div className="login-header">
          <div className="login-icon">🌩️</div>
          <h1 className="login-title">CloudBurst</h1>
          <p className="login-subtitle">
            Weather Anomaly Detection System
          </p>
        </div>

        {/* Form */}
        <form className="login-form" onSubmit={handleLogin} noValidate>
          <div className="login-field">
            <label className="login-label" htmlFor="username">
              Username
            </label>
            <input
              id="username"
              type="text"
              className="login-input"
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
              disabled={loading}
            />
          </div>

          <div className="login-field">
            <label className="login-label" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              className="login-input"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              disabled={loading}
            />
          </div>

          {error && (
            <div className="login-error" role="alert">
              ⚠️ {error}
            </div>
          )}

          <button
            type="submit"
            className={`login-btn ${loading ? "login-btn--loading" : ""}`}
            disabled={loading}
          >
            {loading ? (
              <span className="login-spinner" />
            ) : (
              "Sign In"
            )}
          </button>
        </form>

        {/* Role hint for dev/demo */}
        <div className="login-roles">
          <span className="role-hint admin">Admin</span>
          <span className="role-sep">·</span>
          <span className="role-hint analyst">Analyst</span>
          <span className="role-sep">·</span>
          <span className="role-hint viewer">Viewer</span>
          <p>
            Don't have an account? <Link to="/register">Create one</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

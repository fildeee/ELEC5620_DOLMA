import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { register } from "../auth.js";

export default function Signup() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await register(form);
      setSuccess(true);
      // Redirect to Sign In after 2 seconds
      setTimeout(() => navigate("/signin"), 2000);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        {!success ? (
          <>
            <h1 className="auth-title">Create Account</h1>
            <p className="auth-subtext">
              Join DOLMA today and start your journey.
            </p>

            <form onSubmit={handleSubmit} className="auth-form">
              <input
                type="text"
                name="name"
                placeholder="Full Name"
                value={form.name}
                onChange={handleChange}
                required
              />
              <input
                type="email"
                name="email"
                placeholder="Email Address"
                value={form.email}
                onChange={handleChange}
                required
              />
              <input
                type="password"
                name="password"
                placeholder="Password"
                value={form.password}
                onChange={handleChange}
                minLength={6}
                required
              />

              {error && <p className="auth-error">{error}</p>}

              <button type="submit" className="btn primary auth-btn" disabled={submitting}>
                {submitting ? "Creating Account..." : "Sign Up"}
              </button>
            </form>

            <p className="auth-footer">
              Already have an account?{" "}
              <span className="auth-link" onClick={() => navigate("/signin")}>
                Sign in
              </span>
            </p>
          </>
        ) : (
          <div className="success-message">
            <h2>✅ Sign up successful!</h2>
            <p>Redirecting to sign in...</p>
          </div>
        )}
      </div>
    </div>
  );
}

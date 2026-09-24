import React, { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { isLoggedIn, login } from "../auth.js";

export default function Signin() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    // Simulate validation (replace with real backend check later)
    console.log("User signed in:", form);

    login(form.email);

    // Instantly route to home page
    navigate("/home", { replace: true });
  };

  // Already signed in: skip the form
  if (isLoggedIn()) {
    return <Navigate to="/home" replace />;
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1 className="auth-title">Welcome Back</h1>
        <p className="auth-subtext">Sign in to continue using DOLMA.</p>

        <form onSubmit={handleSubmit} className="auth-form">
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
            required
          />

          <button type="submit" className="btn primary auth-btn">
            Sign In
          </button>
        </form>

        <p className="auth-footer">
          Don’t have an account?{" "}
          <span className="auth-link" onClick={() => navigate("/signup")}>
            Sign Up
          </span>
        </p>
      </div>
    </div>
  );
}

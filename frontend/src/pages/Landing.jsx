import React from "react";
import { useNavigate } from "react-router-dom";

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="landing-container">
      {/* ===== Navigation Bar ===== */}
      <nav className="navbar">
        <h1 className="logo">DOLMA</h1>
        <div className="nav-buttons">
          <button onClick={() => navigate("/signin")} className="btn">
            Sign In
          </button>
          <button onClick={() => navigate("/signup")} className="btn primary">
            Sign Up
          </button>
        </div>
      </nav>

      {/* ===== Hero Section ===== */}
      <main className="hero">
        <h2 className="tagline">Intelligent Personal Assistant</h2>
        <h1 className="headline">
          Manage your <span className="highlight">events</span>,{" "}
          <span className="highlight">goals</span>, and{" "}
          <span className="highlight">life</span> smarter.
        </h1>
        <p className="subtext">
          Dolma helps you stay organised with AI-powered scheduling, goal
          tracking, and personalised suggestions — all in one place.
        </p>

        <div className="cta">
          <button onClick={() => navigate("/signup")} className="btn primary">
            Get Started
          </button>
          <button onClick={() => navigate("/signin")} className="btn">
            Learn More
          </button>
        </div>
      </main>

      {/* ===== Footer ===== */}
      <footer>
        <p>© 2025 DOLMA | Built by Group 89</p>
      </footer>
    </div>
  );
}

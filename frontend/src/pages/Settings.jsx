import React, { useEffect, useState, useRef } from "react";
import "../App.css";
import { useNavigate } from "react-router-dom";

const HAT_STORAGE_KEY = "dolmaHat";

const HAT_VARIANTS = {
  classic: {
    emoji: "🎩",
    title: "Classic Counsel",
    caption: "Even-keeled guidance for the everyday mix of tasks.",
  },
  strategist: {
    emoji: "🧭",
    title: "Strategist",
    caption: "Great when you need structured planning and sequencing.",
  },
  scholar: {
    emoji: "📚",
    title: "Scholar",
    caption: "Ideal for research, deep work, and detail follow-ups.",
  },
};

const HAT_OPTIONS = [
  { id: "classic", icon: "🎩", title: "Classic Counsel" },
  { id: "strategist", icon: "🧭", title: "Strategist" },
  { id: "scholar", icon: "📚", title: "Scholar" },
];

const isValidHat = (hatId) => Object.prototype.hasOwnProperty.call(HAT_VARIANTS, hatId);

const normalizeHat = (hatId) => (isValidHat(hatId) ? hatId : "classic");

const getStoredHat = () => {
  if (typeof window === "undefined") return "classic";
  const raw = localStorage.getItem(HAT_STORAGE_KEY);
  return normalizeHat(raw || "classic");
};

export default function Settings() {
  const navigate = useNavigate();
  const [selectedHat, setSelectedHat] = useState(getStoredHat);
  const [hatMessage, setHatMessage] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [isExiting, setIsExiting] = useState(false);
  const pageRef = useRef(null);
  const redirectRef = useRef(false);

  // 🌐 Use environment-based backend URL
  const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:5050";

  useEffect(() => {
    fetch(`${API_BASE}/api/google/status`, { credentials: "include" })
      .then((res) => res.json())
      .then((data) => setIsConnected(Boolean(data.connected)))
      .catch(() => setIsConnected(false));
  }, [API_BASE]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = localStorage.getItem(HAT_STORAGE_KEY);
    if (stored) {
      setSelectedHat(normalizeHat(stored));
    }
  }, []);

  useEffect(() => {
    if (!hatMessage) return;
    if (pageRef.current) {
      const node = pageRef.current;
      window.requestAnimationFrame(() => {
        node.scrollTo({ top: node.scrollHeight, behavior: "smooth" });
      });
    }
    const timer = window.setTimeout(() => setHatMessage(""), 2400);
    return () => window.clearTimeout(timer);
  }, [hatMessage]);

  const handleHatChange = (hatId) => {
    const normalized = normalizeHat(hatId);
    setSelectedHat(normalized);
    if (typeof window !== "undefined") {
      localStorage.setItem(HAT_STORAGE_KEY, normalized);
      window.dispatchEvent(new CustomEvent("dolma-hat-change", { detail: { hat: normalized } }));
    }
    const title = HAT_VARIANTS[normalized]?.title || "new look";
    setHatMessage(`Hat updated to ${title}.`);
  };

  const handleGoogleConnect = () => {
    if (isConnected) return;
    window.location.href = `${API_BASE}/api/google/login`;
  };

  const hatMeta = HAT_VARIANTS[selectedHat] || HAT_VARIANTS.classic;
  const handleBack = () => {
    if (!isExiting) {
      redirectRef.current = true;
      setIsExiting(true);
    }
  };

  return (
    <div
      ref={pageRef}
      className={`settings-page${isExiting ? " exiting" : ""}`}
      onAnimationEnd={(event) => {
        if (isExiting && redirectRef.current && event.target === event.currentTarget) {
          navigate("/home", { state: { transition: "fromSettings" } });
          redirectRef.current = false;
        }
      }}
    >
      <header className="settings-hero">
        <div>
          <h1>Personalise DOLMA</h1>
          <p>Manage assistant’s style and calendar integrations.</p>
        </div>
        <div className="settings-hero-preview">
          <span className="settings-hero-badge">{hatMeta.emoji}</span>
          <div className="settings-hero-tagline">
            <span>{hatMeta.title}</span>
            <span>{hatMeta.caption}</span>
          </div>
        </div>
      </header>

      <div className="settings-content">
        <div className="settings-grid">
          <section className="settings-card">
            <h2>Change DOLMA's hat</h2>
            <p className="settings-subtext">Pick the personality that fits the day. Your choice appears instantly in the chat sidebar.</p>
            <div className="hat-options">
              {HAT_OPTIONS.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  className={`hat-btn ${selectedHat === option.id ? "active" : ""}`}
                  onClick={() => handleHatChange(option.id)}
                >
                  <span className="hat-icon">{option.icon}</span>
                  <span className="hat-label">{option.title}</span>
                </button>
              ))}
            </div>
          </section>

          <section className="settings-card">
            <h2>Connect your Google Calendar</h2>
            <p className="settings-subtext">Let DOLMA manage meetings, reminders, and availability with a single click.</p>
            <button
              className={`connect-btn ${isConnected ? "connected" : ""}`}
              onClick={handleGoogleConnect}
              disabled={isConnected}
              title={isConnected ? "Already connected" : "Connect Google Calendar"}
            >
              {isConnected ? "Connected" : "Connect Google Calendar"}
            </button>
          </section>
        </div>

        {hatMessage && <div className="settings-toast">{hatMessage}</div>}
      </div>

      <div className="settings-buttons settings-footer">
        <button className="settings-back-btn" onClick={handleBack}>
          ← Back to Chat
        </button>
      </div>
    </div>
  );
}

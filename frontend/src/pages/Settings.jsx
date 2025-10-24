import React, { useEffect, useState } from "react";
import "../App.css";
import { useNavigate } from "react-router-dom";

export default function Settings() {
  const [selectedHat, setSelectedHat] = useState("default");
  const [isConnected, setIsConnected] = useState(false);
  const navigate = useNavigate();

  // 🌐 Use environment-based backend URL
  const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:5000";

  useEffect(() => {
    // Check connection status on mount
    fetch(`${API_BASE}/api/google/status`, { credentials: "include" })
      .then((res) => res.json())
      .then((data) => setIsConnected(Boolean(data.connected)))
      .catch(() => setIsConnected(false));
  }, []);

  const handleHatChange = (hat) => {
    setSelectedHat(hat);
    alert(`DOLMA is now wearing the ${hat} hat! 🎩`);
  };

  const handleGoogleConnect = () => {
    // Always redirect the browser to localhost (it can’t see the Docker hostname “backend”)
    const backendURL = "http://localhost:5000";
    window.location.href = `${backendURL}/api/google/login`;
  };


  return (
    <div className="settings-page">
      <h1 className="settings-title">Settings</h1>

      {/* Hat Customisation */}
      <section className="settings-section">
        <h2>Change DOLMA's Hat</h2>
        <p className="settings-subtext">
          Customise your assistant’s look by choosing a hat below.
        </p>

        <div className="hat-options">
          <button
            className={`hat-btn ${selectedHat === "default" ? "active" : ""}`}
            onClick={() => handleHatChange("default")}
          >
            🎩 Default Hat
          </button>
          <button
            className={`hat-btn ${selectedHat === "cowboy" ? "active" : ""}`}
            onClick={() => handleHatChange("cowboy")}
          >
            🤠 Cowboy Hat
          </button>
          <button
            className={`hat-btn ${selectedHat === "wizard" ? "active" : ""}`}
            onClick={() => handleHatChange("wizard")}
          >
            🧙 Wizard Hat
          </button>
        </div>
      </section>

      {/* Google Calendar */}
      <section className="settings-section">
        <h2>Connect Your Google Calendar</h2>
        <p className="settings-subtext">
          Let DOLMA manage your schedule by integrating with your Google Calendar.
        </p>
        <button
          className={`connect-btn ${isConnected ? "connected" : ""}`}
          onClick={handleGoogleConnect}
          disabled={isConnected}
          title={isConnected ? "Already connected" : "Connect Google Calendar"}
        >
          {isConnected ? "Connected" : "Connect Google Calendar"}
        </button>
      </section>

      {/* Navigation */}
      <section className="settings-section">
        <button className="connect-btn" onClick={() => navigate("/home")}>
          ← Back to Chat
        </button>
      </section>
    </div>
  );
}

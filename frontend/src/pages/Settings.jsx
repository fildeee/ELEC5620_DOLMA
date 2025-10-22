import React, { useEffect, useState } from "react";
import "../App.css";
import { useNavigate } from "react-router-dom";

export default function Settings() {
  const [selectedHat, setSelectedHat] = useState("default");
  const [isConnected, setIsConnected] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    // Check connection status on mount
    fetch("http://localhost:5000/api/google/status", { credentials: "include" })
      .then(res => res.json())
      .then(data => setIsConnected(Boolean(data.connected)))
      .catch(() => setIsConnected(false));
  }, []);

  const handleHatChange = (hat) => {
    setSelectedHat(hat);
    alert(`DOLMA is now wearing the ${hat} hat! 🎩`);
  };

  const handleGoogleConnect = () => {
    // this will redirect the browser to Google
    window.location.href = "http://localhost:5000/api/google/login";
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

      {/* Navigation back to DOLMA page */}
      <section className="settings-section">
        <button
          className="connect-btn"
          onClick={() => navigate("/home")}
        >
          ← Back to Chat
        </button>
      </section>
    </div>
  );
}

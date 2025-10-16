import React, { useState } from "react";
import "../App.css";

export default function Settings() {
  const [selectedHat, setSelectedHat] = useState("default");
  const [isConnected, setIsConnected] = useState(false);

  const handleHatChange = (hat) => {
    setSelectedHat(hat);
    alert(`DOLMA is now wearing the ${hat} hat! 🎩`);
  };

  const handleGoogleConnect = () => {
    setIsConnected(true);
    alert("Google Calendar connected successfully!");
  };

  return (
    <div className="settings-page">
      <h1 className="settings-title">Settings</h1>

      {/* ===== Section: Hat Customisation ===== */}
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

      {/* ===== Section: Google Calendar ===== */}
      <section className="settings-section">
        <h2>Connect Your Google Calendar</h2>
        <p className="settings-subtext">
          Let DOLMA manage your schedule by integrating with your Google
          Calendar.
        </p>
        <button
          className={`connect-btn ${isConnected ? "connected" : ""}`}
          onClick={handleGoogleConnect}
        >
          {isConnected ? "Connected ✅" : "Connect Google Calendar"}
        </button>
      </section>
    </div>
  );
}

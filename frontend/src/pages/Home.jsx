import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import dolmaFace from "../assets/dolma_face.png";

function TipsCard({ tips, place, weather }) {
  const card = {
    marginTop: "10px",
    background: "linear-gradient(180deg, #f8fbff 0%, #f1f6ff 100%)",
    border: "1px solid #d6e4ff",
    borderRadius: "10px",
    padding: "12px 14px",
    maxWidth: "640px",
    color: "#1f2d3d",
    boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
  };
  const header = {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 8,
  };
  const title = { fontWeight: 700, fontSize: 14 };
  const placeStyle = { fontSize: 12, color: "#4a5660" };
  const grid = {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
    gap: "6px 12px",
    marginBottom: tips ? 6 : 0,
  };
  const metric = {
    background: "#ffffff",
    border: "1px solid #e8eefc",
    borderRadius: 8,
    padding: "6px 8px",
    fontSize: 12,
    color: "#25313b",
  };

  const metrics = [];
  if (weather) {
    if (typeof weather.cond === "string" && weather.cond.trim())
      metrics.push({ label: "Weather", value: weather.cond });
    if (typeof weather.temp === "number")
      metrics.push({ label: "Temp", value: `${Math.round(weather.temp)}°C` });
    if (typeof weather.feels === "number")
      metrics.push({
        label: "Feels Like",
        value: `${Math.round(weather.feels)}°C`,
      });
    if (typeof weather.humidity === "number")
      metrics.push({
        label: "Humidity",
        value: `${Math.round(weather.humidity)}%`,
      });
    if (typeof weather.wind === "number")
      metrics.push({ label: "Wind", value: `${weather.wind} m/s` });
  }

  return (
    <div className="tips-card" style={card}>
      <div style={header}>
        <div style={title}>Today's Tips</div>
        <div style={placeStyle}>{place || ""}</div>
      </div>
      {metrics.length > 0 && (
        <div style={grid}>
          {metrics.map((m, idx) => (
            <div key={idx} style={metric}>
              <div style={{ fontSize: 11, color: "#5b6770" }}>{m.label}</div>
              <div style={{ fontWeight: 600 }}>{m.value}</div>
            </div>
          ))}
        </div>
      )}
      {tips && (
        <div style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>{tips}</div>
      )}
    </div>
  );
}

export default function Home() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Hello! I'm DOLMA, your intelligent personal assistant. How can I help you today?",
    },
  ]);
  const [input, setInput] = useState("");
  const [coords, setCoords] = useState(null);
  const [locError, setLocError] = useState(null);
  const [locInfo, setLocInfo] = useState(null);
  const [permState, setPermState] = useState(null);
  const chatEndRef = useRef(null);
  const navigate = useNavigate();

  // 🌐 Base URL from .env (VITE_API_BASE)
  const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:5000";

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMsg = { role: "user", text: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    const filteredConversation = messages.filter(
      (msg) =>
        msg &&
        (msg.role === "user" || msg.role === "assistant") &&
        msg.text.trim() !== ""
    );

    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMsg.text,
          conversation: filteredConversation,
          location: coords,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      console.log("DOLMA response:", data);

      if (data && data.reply && data.reply.trim() !== "") {
        const assistantMsg = { role: "assistant", text: data.reply };
        if (data.tips) {
          assistantMsg.tips = data.tips;
          assistantMsg.place = data.place_name || null;
          assistantMsg.weather = data.weather || null;
        }
        setMessages((prev) => [...prev, assistantMsg]);
      } else if (data.error) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: `⚠️ ${data.error}` },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            text: "Hmm… something went wrong. Please try again.",
          },
        ]);
      }
    } catch (err) {
      console.error("Network or parsing error:", err);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Network error, please try again." },
      ]);
    }
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const requestLocation = () => {
    if (!("geolocation" in navigator)) {
      setLocError("Geolocation not supported by this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords || {};
        if (typeof latitude === "number" && typeof longitude === "number") {
          setCoords({ lat: latitude, lon: longitude });
          setLocError(null);
          setLocInfo(null);
        }
      },
      (err) => {
        setLocError(err?.message || "Unable to get location");
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 }
    );
  };

  useEffect(() => {
    let cancelled = false;
    const checkPerm = async () => {
      try {
        if (navigator.permissions && navigator.permissions.query) {
          const status = await navigator.permissions.query({ name: "geolocation" });
          if (cancelled) return;
          setPermState(status.state);
          status.onchange = () => setPermState(status.state);
          if (status.state === "granted") {
            requestLocation();
          } else if (status.state === "prompt") {
            requestLocation();
          } else if (status.state === "denied") {
            try {
              const resp = await fetch("https://ipapi.co/json/");
              const j = await resp.json();
              if (
                j &&
                typeof j.latitude === "number" &&
                typeof j.longitude === "number"
              ) {
                setCoords({ lat: j.latitude, lon: j.longitude });
                setLocInfo("Using approximate location based on IP.");
              }
            } catch (_) {}
          }
        } else {
          requestLocation();
        }
      } catch (_) {
        requestLocation();
      }
    };
    checkPerm();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="dolma-layout">
      <aside className="dolma-sidebar">
        <div className="sidebar-header">
          <h2 className="sidebar-logo">DOLMA</h2>
          <div className="dolma-avatar">
            <img src={dolmaFace} alt="Dolma avatar" />
            <p className="avatar-caption">Your AI Assistant</p>
          </div>
        </div>

        <div className="sidebar-footer">
          <button className="sidebar-btn" onClick={() => navigate("/settings")}>
            ⚙️ Settings
          </button>
          <button
            className="sidebar-btn"
            onClick={() => {
              alert("Logged out!");
              navigate("/signin");
            }}
          >
            Logout
          </button>
        </div>
      </aside>

      <main className="dolma-chat">
        <div className="chat-messages">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`message-row ${
                msg.role === "user" ? "user" : "assistant"
              }`}
            >
              <div className="message-bubble">{msg.text}</div>
              {msg.tips && (
                <TipsCard
                  tips={msg.tips}
                  place={msg.place}
                  weather={msg.weather}
                />
              )}
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        <form className="chat-input-bar" onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Ask DOLMA anything..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="chat-input"
          />
          <button type="submit" className="send-btn">
            ➤
          </button>
        </form>

        {(locError || locInfo) && (
          <div className="message-row assistant">
            <div className="message-bubble">
              {locInfo ? (
                <span>{locInfo}</span>
              ) : (
                <span>
                  Tip: Allow location access for local weather and events. ({locError})
                </span>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

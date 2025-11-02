import React, { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import dolmaFace from "../assets/dolma_face.png";
import hat_classic from "../assets/hat_classic.png";
import hat_scholar from "../assets/hat_scholar.png";
import hat_strategist from "../assets/hat_strategist.png";

const CATEGORY_UNITS = {
  fitness: "KM",
  study: "pages",
  finance: "$",
  hours: "hours",
  other: "",
};

const HAT_STORAGE_KEY = "dolmaHat";
const HAT_VARIANTS = {
  hat_classic: {
    src: hat_classic,
    title: "Classic Counsel",
  },
  hat_scholar: {
    src: hat_scholar,
    title: "Scholar",
  },
  hat_strategist: {
    src: hat_strategist,
    title: "Strategist",
  },
};

const LEGACY_HAT_MAP = {
  classic: "hat_classic",
  scholar: "hat_scholar",
  strategist: "hat_strategist",
};

const readStoredHat = () => {
  if (typeof window === "undefined") return "hat_classic";
  const raw = localStorage.getItem(HAT_STORAGE_KEY);

  if (raw && HAT_VARIANTS[raw]) return raw;

  if (raw && LEGACY_HAT_MAP[raw]) return LEGACY_HAT_MAP[raw];

  return "hat_classic";
};




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

// renders label/value rows under a message
function KVList({ items }) {
  if (!items || !items.length) return null;
  return (
    <dl style={{ marginTop: 6, marginBottom: 0 }}>
      {items.map((it, idx) => (
        <div key={idx} style={{ display: "flex", gap: 8, marginBottom: 4 }}>
          <dt style={{ minWidth: 84, color: "#5b6770" }}>{it.label}</dt>
          <dd style={{ margin: 0, fontWeight: 600 }}>{it.value}</dd>
        </div>
      ))}
    </dl>
  );
}

// removes md formatting from text
const stripMD = (s) => (s ?? "").replace(/\*\*/g, "").trim();


export default function Home() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Hello! I'm DOLMA, your intelligent personal assistant. How can I help you today?",
    },
  ]);
  const [hat, setHat] = useState(readStoredHat);
  const [isEntering, setIsEntering] = useState(false);
  const [input, setInput] = useState("");
  const [coords, setCoords] = useState(null);
  const [locError, setLocError] = useState(null);
  const [locInfo, setLocInfo] = useState(null);
  const [permState, setPermState] = useState(null);
  const [goals, setGoals] = useState([]);
  const [goalForm, setGoalForm] = useState({
    title: "",
    description: "",
    target_date: "",
    target_value: "",
    category: "fitness",
    custom_unit: "",
  });
  const [progressDrafts, setProgressDrafts] = useState({});
  const [goalError, setGoalError] = useState(null);
  const [goalMessage, setGoalMessage] = useState(null);
  const [goalLoading, setGoalLoading] = useState(false);
  const [goalSaving, setGoalSaving] = useState(false);
  const chatEndRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();

  // 🌐 Base URL from .env (VITE_API_BASE) with sensible fallbacks
  const resolveApiBase = () => {
    const raw = import.meta.env.VITE_API_BASE;
    if (typeof raw === "string" && raw.trim()) {
      const cleaned = raw.trim().replace(/\/+$/, "");
      if (!/^https?:\/\//i.test(cleaned)) {
        console.warn(
          `[DOLMA] VITE_API_BASE lacks protocol, defaulting to http://: ${cleaned}`
        );
        return `http://${cleaned}`;
      }
      return cleaned;
    }
    if (typeof window !== "undefined") {
      const { protocol, hostname } = window.location;
      const defaultPort = protocol === "https:" ? "5001" : "5000";
      return `${protocol}//${hostname}:${defaultPort}`;
    }
    return "http://localhost:5000";
  };

  const API_BASE = resolveApiBase();
  const apiUrl = (path) => `${API_BASE}${path}`;
  const formatNumber = (value) => {
    if (typeof value !== "number" || Number.isNaN(value)) {
      return null;
    }
    const rounded = Math.round(value);
    if (Math.abs(value - rounded) < 1e-6) {
      return String(rounded);
    }
    return value.toFixed(1).replace(/\.0$/, "");
  };
  const formatWithUnit = (value, unitSymbol) => {
    if (value === null || value === undefined) return null;
    const numText = formatNumber(value);
    if (!numText) return null;
    if (!unitSymbol) return numText;
    if (unitSymbol === "$") return `$${numText}`;
    if (unitSymbol.toLowerCase() === "hours") {
      return `${numText} hours`;
    }
    return `${numText} ${unitSymbol}`;
  };
  const hatMeta = HAT_VARIANTS[hat] || HAT_VARIANTS.classic;

  const fetchGoals = useCallback(async () => {
    try {
      setGoalLoading(true);
      setGoalError(null);
      const resp = await fetch(apiUrl("/api/goals"));
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        throw new Error(data?.error || `HTTP ${resp.status}`);
      }
      setGoals(Array.isArray(data.goals) ? data.goals : []);
    } catch (err) {
      console.error("Fetch goals error:", err);
      setGoalError(
        err?.message
          ? `Unable to load goals: ${err.message}`
          : "Unable to load goals right now."
      );
    } finally {
      setGoalLoading(false);
    }
  }, [API_BASE]);

  useEffect(() => {
    fetchGoals();
  }, [fetchGoals]);

  useEffect(() => {
    console.info("[DOLMA] API base URL:", API_BASE);
  }, [API_BASE]);

  useEffect(() => {
    if (location.state?.transition === "fromSettings") {
      setIsEntering(true);
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location.state, location.pathname, navigate]);

  useEffect(() => {
    if (!isEntering) return;
    const timer = window.setTimeout(() => setIsEntering(false), 400);
    return () => window.clearTimeout(timer);
  }, [isEntering]);

  useEffect(() => {
  if (typeof window === "undefined") return;

  const syncHat = () => setHat(readStoredHat());

  const handleStorage = (event) => {
    if (event.key !== HAT_STORAGE_KEY) return;
    const incoming = event.newValue;

    if (incoming && HAT_VARIANTS[incoming]) {
      setHat(incoming);
    } else if (incoming && LEGACY_HAT_MAP[incoming]) {
      setHat(LEGACY_HAT_MAP[incoming]);
    } else {
      setHat("hat_classic");
    }
  };

  const handleCustom = (event) => {
    const incoming = event?.detail?.hat;
    if (incoming && HAT_VARIANTS[incoming]) {
      setHat(incoming);
    } else if (incoming && LEGACY_HAT_MAP[incoming]) {
      setHat(LEGACY_HAT_MAP[incoming]);
    } else {
      syncHat();
    }
  };

  window.addEventListener("storage", handleStorage);
  window.addEventListener("dolma-hat-change", handleCustom);
  syncHat();

  return () => {
    window.removeEventListener("storage", handleStorage);
    window.removeEventListener("dolma-hat-change", handleCustom);
  };
}, []);

  useEffect(() => {
    setProgressDrafts((prev) => {
      const next = {};
      (goals || []).forEach((goal) => {
        if (!goal || !goal.id) {
          return;
        }
        if (Object.prototype.hasOwnProperty.call(prev, goal.id)) {
          next[goal.id] = prev[goal.id];
        } else {
          next[goal.id] = String(
            typeof goal.progress === "number" ? goal.progress : 0
          );
        }
      });
      return next;
    });
  }, [goals]);

  useEffect(() => {
    if (!goalMessage) return;
    const timer = setTimeout(() => setGoalMessage(null), 4000);
    return () => clearTimeout(timer);
  }, [goalMessage]);

  const applyGoalUpdate = useCallback(
    async (goalId, payload, successText) => {
      try {
        setGoalError(null);
        setGoalMessage(null);
        const resp = await fetch(apiUrl(`/api/goals/${goalId}`), {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) {
          throw new Error(data.error || `HTTP ${resp.status}`);
        }
        const { system_message, ...goalData } = data;
        setGoals((prev) =>
          prev.map((goal) => (goal.id === goalId ? goalData : goal))
        );
        setProgressDrafts((prev) => ({
          ...prev,
          [goalId]: String(goalData.progress ?? 0),
        }));
        setGoalMessage(successText || "Goal updated.");
        if (system_message) {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", text: system_message },
          ]);
        }
      } catch (err) {
        console.error("Update goal error:", err);
        setGoalError(err.message || "Unable to update goal.");
      }
    },
    [API_BASE]
  );

  const handleGoalSubmit = async (e) => {
    e.preventDefault();
    const trimmedTitle = goalForm.title.trim();
    if (!trimmedTitle) {
      setGoalError("Please give your goal a title.");
      return;
    }
    setGoalSaving(true);
    setGoalMessage(null);
    setGoalError(null);
    try {
      const payload = { title: trimmedTitle };
      if (goalForm.description.trim()) {
        payload.description = goalForm.description.trim();
      }
      if (goalForm.target_date) {
        payload.target_date = goalForm.target_date;
      }
      const rawTarget = String(goalForm.target_value || "").trim();
      if (!rawTarget) {
        setGoalError("Please set a target amount.");
        setGoalSaving(false);
        return;
      }
      const numericTarget = Number(rawTarget);
      if (Number.isNaN(numericTarget) || numericTarget <= 0) {
        setGoalError("Target amount must be a positive number.");
        setGoalSaving(false);
        return;
      }
      payload.target_value = numericTarget;
      const category = goalForm.category || "fitness";
      let unitSymbol = CATEGORY_UNITS[category] || "";
      if (category === "other") {
        const customUnit = goalForm.custom_unit.trim();
        if (!customUnit) {
          setGoalError("Please provide a unit label for this goal.");
          setGoalSaving(false);
          return;
        }
        unitSymbol = customUnit;
      }
      payload.target_unit = unitSymbol;
      payload.progress_value = 0;
      const resp = await fetch(apiUrl("/api/goals"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        throw new Error(data.error || `HTTP ${resp.status}`);
      }
      setGoals((prev) => [...prev, data]);
      setGoalForm({
        title: "",
        description: "",
        target_date: "",
        target_value: "",
        category: goalForm.category,
        custom_unit: category === "other" ? goalForm.custom_unit : "",
      });
      setGoalMessage("Goal saved!");
    } catch (err) {
      console.error("Create goal error:", err);
      setGoalError(err.message || "Unable to save goal.");
    } finally {
      setGoalSaving(false);
    }
  };

  const handleProgressDraftChange = (goalId, value) => {
    setProgressDrafts((prev) => ({
      ...prev,
      [goalId]: value,
    }));
  };

  const handleProgressApply = async (goalId) => {
    const raw = progressDrafts[goalId];
    const numeric = Number(raw);
    if (Number.isNaN(numeric)) {
      setGoalError("Progress must be a number between 0 and 100.");
      return;
    }
    const bounded = Math.max(0, Math.min(100, numeric));
    await applyGoalUpdate(goalId, { progress: bounded }, "Progress updated.");
  };

  const handleGoalComplete = (goalId) =>
    applyGoalUpdate(
      goalId,
      { progress: 100, status: "completed" },
      "Nice work! Goal marked complete."
    );

  const handleGoalArchive = (goalId) =>
    applyGoalUpdate(goalId, { status: "archived" }, "Goal archived.");

  const handleGoalActivate = (goalId) =>
    applyGoalUpdate(goalId, { status: "active" }, "Goal reactivated.");

  const handleGoalDelete = async (goalId) => {
    if (typeof window !== "undefined" && !window.confirm("Remove this goal?")) {
      return;
    }
    try {
      setGoalError(null);
      setGoalMessage(null);
      const resp = await fetch(apiUrl(`/api/goals/${goalId}`), {
        method: "DELETE",
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        throw new Error(data?.error || `HTTP ${resp.status}`);
      }
      const { system_message } = data;
      setGoals((prev) => prev.filter((goal) => goal.id !== goalId));
      setProgressDrafts((prev) => {
        const next = { ...prev };
        delete next[goalId];
        return next;
      });
      setGoalMessage("Goal removed.");
      if (system_message) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: system_message },
        ]);
      }
    } catch (err) {
      console.error("Delete goal error:", err);
      setGoalError(err.message || "Unable to delete goal.");
    }
  };

  const handleGoalRefresh = () => {
    fetchGoals();
  };

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
      const response = await fetch(apiUrl("/api/chat"), {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMsg.text,
          conversation: filteredConversation,
          location: coords,
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data?.error || `HTTP ${response.status}`);
      }
      console.log("DOLMA response:", data);

      if (Array.isArray(data.goals)) {
        setGoals(data.goals);
      }

      // builds a single assistant message that prefers structured fields if present
      const assistantMsg = {
        role: "assistant",
        text: data.reply || "",
        reply_md: data.reply_md || null,
        items: Array.isArray(data.items) ? data.items : null, // [{label, value}]
        cta: data.cta || null, // line for confirm/cancel prompt
        tips: data.tips,
        place: data.place_name || null,
        weather: data.weather || null,
      };

      if (assistantMsg.text || assistantMsg.reply_md || assistantMsg.items || assistantMsg.cta) {
        setMessages((prev) => [...prev, assistantMsg]);
      } else if (data.error) {
        setMessages((prev) => [...prev, { role: "assistant", text: ` ${data.error}` }]);
      } else {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: "Hmm… something went wrong. Please try again." },
        ]);
      }
    } catch (err) {
      console.error("Network or parsing error:", err);
      const message =
        err?.message && err.message !== "Failed to fetch"
          ? ` ${err.message}`
          : "Network error, please try again.";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: message },
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
    <div className={`dolma-layout${isEntering ? " entering" : ""}`}>
      <aside className="dolma-sidebar">
        <div className="sidebar-header">
          <h2 className="sidebar-logo">DOLMA</h2>
          <div className="dolma-avatar">
           <div className="avatar-frame">
              <img src={dolmaFace} alt="Dolma avatar" />
              {hatMeta?.src && (
                <img src={hatMeta.src} alt="Dolma hat" className="avatar-hat" />
              )}
            </div>
            <p className="avatar-caption">{hatMeta?.title || "Your AI Assistant"}</p>
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
        <div className="chat-pane">
          <div className="chat-messages">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`message-row ${
                  msg.role === "user" ? "user" : "assistant"
                }`}
              >
                <div className="message-bubble">
                  <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.4 }}>
                    {stripMD(msg.reply_md ?? msg.text)}
                  </div>

                  {/* key/value lines */}
                  <KVList items={msg.items} />

                  {/* confirm/cancel inline controls */}
                  {msg.cta && (
                    <div style={{ marginTop: 10, display: "flex", alignItems: "center", gap: 8 }}>
                      <span>{msg.cta}</span>
                    </div>
                  )}
                </div>
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

          {(locError || locInfo) && (
            <div className="system-tip">
              {locInfo ? (
                <span>{locInfo}</span>
              ) : (
                <span>
                  Tip: Allow location access for local weather and events. ({locError})
                </span>
              )}
            </div>
          )}

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
        </div>

        <aside className="goals-pane">
          <div className="goals-header">
            <h3>Goal Tracker</h3>
            <button
              type="button"
              className="goals-refresh"
              onClick={handleGoalRefresh}
              disabled={goalLoading}
              title="Refresh goals"
            >
              ⟳
            </button>
          </div>

          {goalMessage && <div className="goal-toast success">{goalMessage}</div>}
          {goalError && <div className="goal-toast error">{goalError}</div>}

          <form className="goal-form" onSubmit={handleGoalSubmit}>
            <input
              type="text"
              placeholder="What goal should we track?"
              value={goalForm.title}
              onChange={(e) =>
                setGoalForm((prev) => ({ ...prev, title: e.target.value }))
              }
            />
            <div className="goal-form-row">
              <input
                type="number"
                min="0"
                step="any"
                placeholder="Target amount"
                value={goalForm.target_value}
                onChange={(e) =>
                  setGoalForm((prev) => ({
                    ...prev,
                    target_value: e.target.value,
                  }))
                }
              />
              <select
                className="unit-select"
                value={goalForm.category}
                onChange={(e) =>
                  setGoalForm((prev) => ({
                    ...prev,
                    category: e.target.value,
                    custom_unit: e.target.value === "other" ? prev.custom_unit : "",
                  }))
                }
              >
                <option value="fitness">Fitness (km)</option>
                <option value="study">Study (pages)</option>
                <option value="finance">Finance ($)</option>
                <option value="hours">Focus (hours)</option>
                <option value="other">Other unit…</option>
              </select>
              {goalForm.category === "other" && (
                <input
                  type="text"
                  className="custom-unit-input"
                  placeholder="Unit label (e.g. reps)"
                  value={goalForm.custom_unit}
                  onChange={(e) =>
                    setGoalForm((prev) => ({
                      ...prev,
                      custom_unit: e.target.value,
                    }))
                  }
                />
              )}
            </div>
            <textarea
              rows="3"
              placeholder="Optional details"
              value={goalForm.description}
              onChange={(e) =>
                setGoalForm((prev) => ({
                  ...prev,
                  description: e.target.value,
                }))
              }
            />
            <div className="goal-form-row">
              <input
                type="date"
                value={goalForm.target_date}
                onChange={(e) =>
                  setGoalForm((prev) => ({
                    ...prev,
                    target_date: e.target.value,
                  }))
                }
              />
              <button type="submit" disabled={goalSaving}>
                {goalSaving ? "Saving…" : "Add Goal"}
              </button>
            </div>
          </form>

          <div className="goal-list">
            {goalLoading ? (
              <p className="goal-placeholder">Loading goals…</p>
            ) : goals.length === 0 ? (
              <p className="goal-placeholder">
                No goals yet. Let’s create one!
              </p>
            ) : (
              goals.map((goal) => {
                const description = (goal.description || "").trim();
                const draftPercent =
                  progressDrafts[goal.id] !== undefined
                    ? progressDrafts[goal.id]
                    : String(goal.progress ?? 0);
                const targetValue =
                  typeof goal.target_value === "number" ? goal.target_value : null;
                let progressValue =
                  typeof goal.progress_value === "number"
                    ? goal.progress_value
                    : null;
                const progressPct =
                  typeof goal.progress === "number" ? goal.progress : 0;
                const clampedProgress = Math.max(
                  0,
                  Math.min(100, progressPct)
                );
                const unitLabel = (goal.target_unit || "").trim();
                if (progressValue === null && targetValue !== null) {
                  progressValue = (targetValue * progressPct) / 100;
                }
                const remainingValue =
                  targetValue !== null && progressValue !== null
                    ? Math.max(targetValue - progressValue, 0)
                    : null;
                const targetDisplay =
                  targetValue !== null ? formatWithUnit(targetValue, unitLabel) : null;
                const remainingDisplay =
                  remainingValue !== null ? formatWithUnit(remainingValue, unitLabel) : null;
                const completedDisplay =
                  progressValue !== null ? formatWithUnit(progressValue, unitLabel) : null;
                return (
                  <div className="goal-card" key={goal.id}>
                    <div className="goal-card-header">
                      <div>
                        <h4>{goal.title || "Untitled goal"}</h4>
                        {description && <p>{description}</p>}
                      </div>
                      <span
                        className={`goal-status badge-${goal.status || "active"}`}
                      >
                        {goal.status || "active"}
                      </span>
                    </div>
                    <div className="goal-meta">
                      <span>
                        Progress: {progressPct}%
                        {completedDisplay ? ` (${completedDisplay})` : ""}
                      </span>
                      {targetDisplay && (
                        <span>
                          Target: {targetDisplay}
                          {goal.target_date ? ` (due ${goal.target_date})` : ""}
                        </span>
                      )}
                      {!targetDisplay && goal.target_date && <span>Due: {goal.target_date}</span>}
                      {targetDisplay && remainingDisplay !== null && remainingValue !== null && remainingValue > 0 && (
                        <span>
                          Remaining: {remainingDisplay}
                        </span>
                      )}
                    </div>
                    <div className="goal-progress">
                      <div
                        className="goal-progress-bar"
                        style={{ width: `${clampedProgress}%` }}
                      />
                    </div>
                    <div className="goal-controls">
                      <div className="progress-input">
                        <input
                          type="number"
                          min="0"
                          max="100"
                          value={draftPercent}
                          onChange={(e) =>
                            handleProgressDraftChange(goal.id, e.target.value)
                          }
                          placeholder="%"
                        />
                        <button
                          type="button"
                          onClick={() => handleProgressApply(goal.id)}
                        >
                          Update
                        </button>
                      </div>
                      <div className="goal-buttons">
                        <button
                          type="button"
                          className="complete-btn"
                          onClick={() => handleGoalComplete(goal.id)}
                          disabled={goal.status === "completed"}
                        >
                          ✓ Complete
                        </button>
                        {goal.status !== "archived" && (
                          <button
                            type="button"
                            onClick={() => handleGoalArchive(goal.id)}
                          >
                            Archive
                          </button>
                        )}
                        {goal.status === "archived" && (
                          <button
                            type="button"
                            onClick={() => handleGoalActivate(goal.id)}
                          >
                            Activate
                          </button>
                        )}
                        <button
                          type="button"
                          className="danger"
                          onClick={() => handleGoalDelete(goal.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </aside>
      </main>
    </div>
  );
}

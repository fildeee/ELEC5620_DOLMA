import React, { useState, useRef, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import dolmaFace from "../assets/dolma_face.png";
import hat_classic from "../assets/hat_classic.png";
import hat_scholar from "../assets/hat_scholar.png";
import hat_strategist from "../assets/hat_strategist.png";
import { getCurrentUser, logout } from "../auth.js";

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

// renders the places a find_places lookup returned, mirroring TipsCard
function PlacesCard({ places, category }) {
  if (!Array.isArray(places) || places.length === 0) return null;

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
  const source = { fontSize: 12, color: "#4a5660" };
  const row = {
    background: "#ffffff",
    border: "1px solid #e8eefc",
    borderRadius: 8,
    padding: "8px 10px",
    marginBottom: 6,
  };
  const nameLine = {
    display: "flex",
    alignItems: "baseline",
    justifyContent: "space-between",
    gap: 10,
  };
  const name = { fontWeight: 600, fontSize: 13, color: "#25313b" };
  const distance = { fontSize: 12, color: "#0084ff", whiteSpace: "nowrap" };
  const detail = { fontSize: 12, color: "#4a5660", marginTop: 3 };
  // OpenStreetMap opening hours run long ("Mo-We 12:00-00:00; Th ..."), so keep
  // them to one line and put the full string in the tooltip.
  const oneLine = {
    ...detail,
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  };
  const unlisted = { ...detail, fontStyle: "italic", color: "#8a949c" };

  const formatDistance = (metres) => {
    if (typeof metres !== "number") return null;
    return metres < 1000 ? `${metres} m` : `${(metres / 1000).toFixed(1)} km`;
  };

  return (
    <div className="places-card" style={card}>
      <div style={header}>
        <div style={title}>
          Nearby{category ? ` \u00b7 ${category}` : ""}
        </div>
        <div style={source}>{places.length} from OpenStreetMap</div>
      </div>

      {places.map((place, idx) => (
        <div key={`${place.name}-${idx}`} style={row}>
          <div style={nameLine}>
            <span style={name}>{place.name}</span>
            <span style={distance}>{formatDistance(place.distance_m)}</span>
          </div>

          {/* shown either way: a blank line would read as "no address needed" */}
          {place.address ? (
            <div style={detail}>{place.address}</div>
          ) : (
            <div style={unlisted}>Address not listed</div>
          )}

          {place.opening_hours && (
            <div style={oneLine} title={place.opening_hours}>
              {place.opening_hours}
            </div>
          )}

          {place.website && (
            <div style={detail}>
              <a
                href={place.website}
                target="_blank"
                rel="noreferrer"
                style={{ color: "#0084ff" }}
              >
                Website
              </a>
            </div>
          )}
        </div>
      ))}
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
  const hatMeta = HAT_VARIANTS[hat] || HAT_VARIANTS.hat_classic;

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
        places: Array.isArray(data.places) ? data.places : null,
        placesCategory: data.places_category || null,
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

  const currentUser = getCurrentUser();

  const handleLogout = async () => {
    if (!window.confirm("Log out of DOLMA?")) return;
    await logout();
    navigate("/signin", { replace: true });
  };

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
          {currentUser && (
            <p className="sidebar-user" title={currentUser.email}>
              {currentUser.email}
            </p>
          )}
          <button className="sidebar-btn logout-btn" onClick={handleLogout}>
            ⎋ Log out
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
                {msg.places && (
                  <PlacesCard places={msg.places} category={msg.placesCategory} />
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

      </main>
    </div>
  );
}

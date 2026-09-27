// Client helpers for the backend's session-based auth (/api/auth/*).
// The server is the source of truth; the current user is cached in memory
// once it has been confirmed so pages can read it synchronously.

function resolveApiBase() {
  const raw = import.meta.env.VITE_API_BASE;
  if (typeof raw === "string" && raw.trim()) {
    const cleaned = raw.trim().replace(/\/+$/, "");
    return /^https?:\/\//i.test(cleaned) ? cleaned : `http://${cleaned}`;
  }
  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:${protocol === "https:" ? "5001" : "5000"}`;
  }
  return "http://localhost:5000";
}

const API_BASE = resolveApiBase();

let currentUser = null;

async function request(path, body) {
  let resp;
  try {
    resp = await fetch(`${API_BASE}${path}`, {
      method: body === undefined ? "GET" : "POST",
      credentials: "include",
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new Error("Cannot reach the server. Please try again later.");
  }
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const err = new Error(data.error || `Request failed (${resp.status})`);
    err.status = resp.status;
    throw err;
  }
  return data;
}

export function getCurrentUser() {
  return currentUser;
}

// Returns the logged-in user, or null if there is no valid session.
export async function fetchCurrentUser() {
  try {
    const data = await request("/api/auth/me");
    currentUser = data.user;
  } catch {
    currentUser = null;
  }
  return currentUser;
}

export async function register({ name, email, password }) {
  const data = await request("/api/auth/register", { name, email, password });
  return data.user;
}

export async function login(email, password) {
  const data = await request("/api/auth/login", { email, password });
  currentUser = data.user;
  return currentUser;
}

export async function logout() {
  try {
    await request("/api/logout", {});
  } catch {
    // Backend unreachable: still drop the local state
  }
  currentUser = null;
}

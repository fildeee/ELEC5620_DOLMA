// Minimal client-side auth state. Sign-in is still simulated, so this only
// records which user is "logged in" so pages can be guarded and logout works.
const AUTH_STORAGE_KEY = "dolmaAuthUser";

export function getCurrentUser() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function isLoggedIn() {
  return Boolean(getCurrentUser());
}

export function login(email) {
  try {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({ email }));
  } catch {
    // ignore storage failures (private mode etc.)
  }
}

export function logout() {
  try {
    localStorage.removeItem(AUTH_STORAGE_KEY);
  } catch {
    // ignore
  }
}

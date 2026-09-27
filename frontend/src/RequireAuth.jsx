import React, { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { fetchCurrentUser, getCurrentUser } from "./auth.js";

// Renders children only for a logged-in user; otherwise redirects to sign-in.
export default function RequireAuth({ children }) {
  const [status, setStatus] = useState(getCurrentUser() ? "ok" : "checking");

  useEffect(() => {
    let cancelled = false;
    fetchCurrentUser().then((user) => {
      if (!cancelled) setStatus(user ? "ok" : "denied");
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (status === "denied") return <Navigate to="/signin" replace />;
  if (status === "checking") return <div className="auth-page" />;
  return children;
}

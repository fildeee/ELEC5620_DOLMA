import React from "react";
import { Navigate } from "react-router-dom";
import { isLoggedIn } from "./auth.js";

// Redirects to the sign-in page when no user is logged in.
export default function RequireAuth({ children }) {
  if (!isLoggedIn()) {
    return <Navigate to="/signin" replace />;
  }
  return children;
}

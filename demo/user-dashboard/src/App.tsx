import { useState } from "react";
import { UserPanel } from "./components/UserPanel";
import { RoleGuard } from "./components/RoleGuard";
import type { UserToken } from "./types/user";

// Two demo tokens — one works, one triggers the UI bug
const LEGACY_USER: UserToken = {
  sub: "user-456",
  email: "legacy@example.com",
  roles: ["admin", "viewer"],
};

const KEYCLOAK_USER: UserToken = {
  sub: "user-123",
  email: "dev@example.com",
  // No top-level roles — Keycloak nests them under realm_access
  realm_access: { roles: ["admin", "user"] },
};

export default function App() {
  const [activeUser, setActiveUser] = useState<UserToken>(LEGACY_USER);

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", maxWidth: 720, margin: "2rem auto", padding: "0 1rem" }}>
      <h1 style={{ fontSize: "1.5rem", marginBottom: "0.25rem" }}>User Dashboard</h1>
      <p style={{ color: "#666", marginTop: 0 }}>Governance Framework — Rule 7 Demo</p>

      {/* Token switcher */}
      <div style={{ display: "flex", gap: "0.5rem", margin: "1.5rem 0" }}>
        <button
          onClick={() => setActiveUser(LEGACY_USER)}
          style={{
            padding: "0.5rem 1rem",
            borderRadius: 6,
            border: "1px solid #ccc",
            background: activeUser.sub === "user-456" ? "#2563eb" : "#fff",
            color: activeUser.sub === "user-456" ? "#fff" : "#333",
            cursor: "pointer",
          }}
        >
          Legacy Token
        </button>
        <button
          onClick={() => setActiveUser(KEYCLOAK_USER)}
          style={{
            padding: "0.5rem 1rem",
            borderRadius: 6,
            border: "1px solid #ccc",
            background: activeUser.sub === "user-123" ? "#2563eb" : "#fff",
            color: activeUser.sub === "user-123" ? "#fff" : "#333",
            cursor: "pointer",
          }}
        >
          Keycloak Token
        </button>
      </div>

      <UserPanel user={activeUser} />

      <hr style={{ margin: "1.5rem 0", border: "none", borderTop: "1px solid #eee" }} />

      <h2 style={{ fontSize: "1.1rem" }}>Admin Panel</h2>
      <RoleGuard user={activeUser} requiredRole="admin">
        <div style={{ padding: "1rem", background: "#f0fdf4", borderRadius: 8, border: "1px solid #bbf7d0" }}>
          <strong>Admin access granted.</strong>
          <p style={{ margin: "0.5rem 0 0" }}>You can manage users, view audit logs, and configure SSO settings.</p>
        </div>
      </RoleGuard>
    </div>
  );
}

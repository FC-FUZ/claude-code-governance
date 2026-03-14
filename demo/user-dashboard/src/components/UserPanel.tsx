import type { UserToken } from "../types/user";

/**
 * Displays user info and their roles as badges.
 *
 * BUG (planted for Rule 7 demo):
 * This component reads `user.roles` directly — the same flat-array
 * assumption as the auth-service middleware. When a Keycloak token is
 * active, `user.roles` is undefined so the panel renders "No roles
 * assigned" even though the user IS an admin via realm_access.roles.
 *
 * TypeScript compiles fine (roles is optional). The bug is ONLY visible
 * in the browser — which is exactly what Rule 7 catches.
 *
 * Claude will:
 * 1. Fix the role extraction (same logic as auth-service)
 * 2. Try to say "done" — Stop hook blocks (no browser evidence)
 * 3. Open browser, see "No roles assigned" if fix is incomplete
 * 4. Take screenshot → file verification report → THEN complete
 */
export function UserPanel({ user }: { user: UserToken }) {
  // BUG: Only reads flat roles — misses realm_access.roles
  const roles = user.roles ?? [];

  return (
    <div style={{ padding: "1rem", background: "#f8fafc", borderRadius: 8, border: "1px solid #e2e8f0" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ fontWeight: 600 }}>{user.email}</div>
          <div style={{ fontSize: "0.85rem", color: "#64748b" }}>ID: {user.sub}</div>
        </div>
        <div style={{ fontSize: "0.75rem", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em" }}>
          {user.realm_access ? "Keycloak SSO" : "Legacy Auth"}
        </div>
      </div>

      <div style={{ marginTop: "0.75rem" }}>
        <span style={{ fontSize: "0.85rem", color: "#475569" }}>Roles: </span>
        {roles.length > 0 ? (
          roles.map((role) => (
            <span
              key={role}
              style={{
                display: "inline-block",
                padding: "0.15rem 0.5rem",
                margin: "0 0.25rem",
                borderRadius: 999,
                fontSize: "0.8rem",
                fontWeight: 500,
                background: role === "admin" ? "#dbeafe" : "#f1f5f9",
                color: role === "admin" ? "#1e40af" : "#475569",
              }}
            >
              {role}
            </span>
          ))
        ) : (
          <span
            data-testid="no-roles"
            style={{ fontSize: "0.85rem", color: "#ef4444", fontStyle: "italic" }}
          >
            No roles assigned
          </span>
        )}
      </div>
    </div>
  );
}

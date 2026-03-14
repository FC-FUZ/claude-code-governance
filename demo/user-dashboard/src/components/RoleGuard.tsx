import type { ReactNode } from "react";
import type { UserToken } from "../types/user";

/**
 * Conditionally renders children if the user has the required role.
 *
 * BUG (same root cause as UserPanel):
 * Only checks `user.roles` — Keycloak users with realm_access.roles
 * are denied access even when they have the required role.
 *
 * Visually: the Keycloak user sees "Access denied" for the admin panel
 * even though they ARE an admin. This is the kind of silent failure
 * that only a browser screenshot catches — TypeScript and tests pass.
 */
export function RoleGuard({
  user,
  requiredRole,
  children,
}: {
  user: UserToken;
  requiredRole: string;
  children: ReactNode;
}) {
  // BUG: Only checks flat roles — misses realm_access.roles
  const roles = user.roles ?? [];
  const hasRole = roles.some((r) => r.toLowerCase() === requiredRole.toLowerCase());

  if (!hasRole) {
    return (
      <div
        data-testid="access-denied"
        style={{ padding: "1rem", background: "#fef2f2", borderRadius: 8, border: "1px solid #fecaca" }}
      >
        <strong style={{ color: "#dc2626" }}>Access denied.</strong>
        <p style={{ margin: "0.5rem 0 0", color: "#991b1b", fontSize: "0.9rem" }}>
          You need the <code>{requiredRole}</code> role to view this section.
        </p>
      </div>
    );
  }

  return <>{children}</>;
}

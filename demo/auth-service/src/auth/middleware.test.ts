import { describe, it, mock } from "node:test";
import assert from "node:assert";
import jwt from "jsonwebtoken";

// Simulates the bug: Keycloak-style nested token
const KEYCLOAK_TOKEN_PAYLOAD = {
  sub: "user-123",
  email: "dev@example.com",
  realm_access: {
    roles: ["admin", "user"],
  },
  // No top-level "roles" field — this is the Keycloak format
};

const LEGACY_TOKEN_PAYLOAD = {
  sub: "user-456",
  email: "legacy@example.com",
  roles: ["admin", "viewer"],
};

// This token triggers the TypeError — roles is an object, not an array
const MALFORMED_TOKEN_PAYLOAD = {
  sub: "user-789",
  email: "edge@example.com",
  roles: { admin: true, user: true },
};

const SECRET = "test-secret";

describe("validateToken", () => {
  it("should handle legacy flat-roles tokens", () => {
    const token = jwt.sign(LEGACY_TOKEN_PAYLOAD, SECRET);
    // This works fine — roles is a string array
    const decoded = jwt.verify(token, SECRET) as any;
    assert.ok(Array.isArray(decoded.roles));
  });

  it("should handle Keycloak nested tokens (FAILS — missing realm_access support)", () => {
    const token = jwt.sign(KEYCLOAK_TOKEN_PAYLOAD, SECRET);
    const decoded = jwt.verify(token, SECRET) as any;
    // roles is undefined at top level — extractRoles returns []
    assert.strictEqual(decoded.roles, undefined);
    // The middleware silently returns no roles — access control breaks
  });

  it("should throw TypeError on object-shaped roles (THE BUG)", () => {
    const token = jwt.sign(MALFORMED_TOKEN_PAYLOAD, SECRET);
    const decoded = jwt.verify(token, SECRET) as any;
    // decoded.roles is { admin: true, user: true }
    // Calling .map() on this object throws TypeError
    assert.throws(() => {
      decoded.roles.map((r: string) => r.toLowerCase());
    }, TypeError);
  });
});

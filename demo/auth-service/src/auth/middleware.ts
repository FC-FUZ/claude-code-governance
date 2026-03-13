import jwt from "jsonwebtoken";
import { Request, Response, NextFunction } from "express";

interface TokenPayload {
  sub: string;
  email: string;
  roles: string[];
  iat: number;
  exp: number;
}

const JWT_SECRET = process.env.JWT_SECRET || "dev-secret-change-me";

export function validateToken(req: Request, res: Response, next: NextFunction) {
  const authHeader = req.headers.authorization;
  if (!authHeader?.startsWith("Bearer ")) {
    return res.status(401).json({ error: "Missing token" });
  }

  const token = authHeader.slice(7);
  const payload = jwt.verify(token, JWT_SECRET) as TokenPayload;

  // Extract user claims
  const userId = payload.sub;
  const email = payload.email;
  const roles = extractRoles(payload);

  req.user = { userId, email, roles };
  next();
}

function extractRoles(payload: TokenPayload): string[] {
  // BUG: This assumes roles is always a flat string array.
  // Keycloak tokens nest roles under realm_access.roles,
  // so payload.roles is undefined and this returns [].
  // When downstream code calls roles.includes("admin"),
  // it works (returns false) but role-based access silently breaks.
  //
  // The REAL bug: when payload has realm_access as an object,
  // and someone passes a token where "roles" is actually an object
  // like { admin: true, user: true }, calling .map() on it throws:
  //   TypeError: payload.roles.map is not a function
  if (!payload.roles) {
    return [];
  }
  return payload.roles.map((r: string) => r.toLowerCase());
}

// This is what a Keycloak token actually looks like:
// {
//   "sub": "user-123",
//   "email": "dev@example.com",
//   "realm_access": {
//     "roles": ["admin", "user"]
//   },
//   "resource_access": {
//     "my-app": {
//       "roles": ["app-admin"]
//     }
//   }
// }

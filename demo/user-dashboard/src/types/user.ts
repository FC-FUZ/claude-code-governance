/** Simulated JWT payload — matches auth-service demo format */
export interface UserToken {
  sub: string;
  email: string;
  roles?: string[];
  realm_access?: { roles: string[] };
  resource_access?: Record<string, { roles: string[] }>;
}

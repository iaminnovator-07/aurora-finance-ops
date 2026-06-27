/** API base URL — use relative path in dev (Vite proxy) or absolute in production. */
export const API_BASE =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") || "/api/v1";

export const AUTH_STORAGE_KEY = "aurora_auth";

export type StoredAuth = {
  access_token: string;
  refresh_token: string;
  user: { id: string; email: string; full_name: string; role: string };
};

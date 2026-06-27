import { API_BASE, AUTH_STORAGE_KEY, type StoredAuth } from "./config";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public reason?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type ApiEnvelope<T> = {
  success: boolean;
  message?: string;
  data: T;
  confidence?: number;
};

export function getStoredAuth(): StoredAuth | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as StoredAuth) : null;
  } catch {
    return null;
  }
}

export function setStoredAuth(auth: StoredAuth | null) {
  if (typeof window === "undefined") return;
  if (auth) localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(auth));
  else localStorage.removeItem(AUTH_STORAGE_KEY);
}

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const auth = getStoredAuth();
  if (!auth?.refresh_token) return null;
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: auth.refresh_token }),
        });
        if (!res.ok) return null;
        const json = (await res.json()) as ApiEnvelope<{
          access_token: string;
          refresh_token: string;
        }>;
        const updated = {
          ...auth,
          access_token: json.data.access_token,
          refresh_token: json.data.refresh_token,
        };
        setStoredAuth(updated);
        return updated.access_token;
      } catch {
        return null;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<T> {
  const auth = getStoredAuth();
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (auth?.access_token) {
    headers.set("Authorization", `Bearer ${auth.access_token}`);
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401 && retry && auth?.refresh_token) {
    const newToken = await refreshAccessToken();
    if (newToken) return apiRequest<T>(path, options, false);
    setStoredAuth(null);
  }

  const json = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new ApiError(
      json.message || json.reason || `Request failed (${res.status})`,
      res.status,
      json.code,
      json.reason,
    );
  }

  if (json && typeof json === "object" && "data" in json) {
    return (json as ApiEnvelope<T>).data;
  }
  return json as T;
}

export const api = {
  get: <T>(path: string) => apiRequest<T>(path),
  post: <T>(path: string, body?: unknown) =>
    apiRequest<T>(path, {
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body ?? {}),
    }),
  postForm: <T>(path: string, form: FormData) =>
    apiRequest<T>(path, { method: "POST", body: form }),
};

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, setStoredAuth, getStoredAuth, type StoredAuth } from "@/lib/api/client";
import { AUTH_STORAGE_KEY } from "@/lib/api/config";

type AuthContextValue = {
  auth: StoredAuth | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

// DEV_CREDENTIALS removed. User must explicitly log in.

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<StoredAuth | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      const stored = getStoredAuth();
      if (stored) {
        if (!cancelled) {
          setAuth(stored);
          setIsLoading(false);
        }
        return;
      }
      // Do not auto-login with dev credentials anymore.
      setIsLoading(false);
    }

    bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = async (email: string, password: string) => {
    const data = await api.post<{
      user: StoredAuth["user"];
      tokens: { access_token: string; refresh_token: string };
    }>("/auth/login", { email, password });
    const session: StoredAuth = {
      access_token: data.tokens.access_token,
      refresh_token: data.tokens.refresh_token,
      user: data.user,
    };
    setStoredAuth(session);
    setAuth(session);
  };

  const logout = () => {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    setAuth(null);
  };

  return (
    <AuthContext.Provider value={{ auth, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

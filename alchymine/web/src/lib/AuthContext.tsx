"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";
import {
  loginUser,
  logoutUser,
  registerUser,
  getMe,
  ApiError,
} from "@/lib/api";
import type { AuthUser } from "@/lib/api";

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    promoCode: string,
  ) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing session on mount.  Auth is now cookie-based so we
  // always try /me — the httpOnly access_token cookie is sent automatically.
  // Legacy localStorage tokens are left in place for the migration fallback
  // path in api.ts and will be cleaned up on next explicit login/logout.
  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => {
        // No valid session — clean up any residual localStorage tokens
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    // Clean slate — prevent stale intake/report data from a previous account
    sessionStorage.clear();
    // Tokens are returned in the JSON body for the migration fallback path
    // and also set as httpOnly cookies by the server automatically.
    const tokens = await loginUser(email, password);
    localStorage.setItem("access_token", tokens.access_token);
    localStorage.setItem("refresh_token", tokens.refresh_token);
    const me = await getMe();
    setUser(me);
  }, []);

  const register = useCallback(
    async (email: string, password: string, promoCode: string) => {
      // Clean slate for new accounts
      sessionStorage.clear();
      const tokens = await registerUser(email, password, promoCode);
      localStorage.setItem("access_token", tokens.access_token);
      localStorage.setItem("refresh_token", tokens.refresh_token);
      const me = await getMe();
      setUser(me);
    },
    [],
  );

  const logout = useCallback(async () => {
    // Ask the server to clear the httpOnly cookies, then clean up local state.
    try {
      await logoutUser();
    } catch {
      // Best-effort — proceed with local cleanup even if the API call fails
    }
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    sessionStorage.clear();
    setUser(null);
    // Clear service worker cache to prevent stale data leakage
    if ("caches" in window) {
      caches.keys().then((keys) => {
        keys.forEach((key) => caches.delete(key));
      });
    }
  }, []);

  const value = useMemo(
    () => ({ user, isLoading, login, register, logout }),
    [user, isLoading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}

export { ApiError };

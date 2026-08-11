"use client";

import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { getMe, logout as apiLogout, refreshSession } from "@/lib/api";
import LoginScreen from "./LoginScreen";

const Ctx = createContext<{ userId: string | null; signOut: () => Promise<void> }>({
  userId: null,
  signOut: async () => {},
});

export function useAuth() {
  return useContext(Ctx);
}

// Access token is short-lived (15 min server-side default) — proactively refresh
// well within that window so an open tab never hits a hard session expiry.
const REFRESH_INTERVAL_MS = 10 * 60 * 1000;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [userId, setUserId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function checkSession() {
    const me = await getMe();
    setUserId(me?.user_id ?? null);
  }

  useEffect(() => {
    checkSession().finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!userId) return;
    intervalRef.current = setInterval(async () => {
      const ok = await refreshSession();
      if (!ok) setUserId(null);
    }, REFRESH_INTERVAL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [userId]);

  async function signOut() {
    await apiLogout();
    setUserId(null);
  }

  if (loading) return null;
  if (!userId) return <LoginScreen onSuccess={checkSession} />;

  return <Ctx.Provider value={{ userId, signOut }}>{children}</Ctx.Provider>;
}

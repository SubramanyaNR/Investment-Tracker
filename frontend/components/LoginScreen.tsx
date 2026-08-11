"use client";

import { useState, type FormEvent } from "react";
import { login } from "@/lib/api";

export default function LoginScreen({ onSuccess }: { onSuccess: () => void | Promise<void> }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function emailSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      await onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  const inputStyle = {
    background: "var(--bg-base)",
    border: "1px solid var(--border-default)",
    color: "var(--text-primary)",
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-6" style={{ background: "var(--bg-base)" }}>
      <div
        className="w-full max-w-sm rounded-2xl p-7"
        style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)" }}
      >
        <div className="mb-6 text-center">
          <h1 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>
            WealthSignal
          </h1>
          <p className="mt-1 text-xs" style={{ color: "var(--text-secondary)" }}>
            Sign in to your portfolio
          </p>
        </div>

        <form onSubmit={emailSubmit} className="space-y-3">
          <input
            type="email"
            required
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg px-3 py-2.5 text-sm outline-none"
            style={inputStyle}
          />
          <input
            type="password"
            required
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg px-3 py-2.5 text-sm outline-none"
            style={inputStyle}
          />

          {error && <p className="text-xs text-red-400">{error}</p>}

          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-lg py-2.5 text-sm font-semibold text-white transition-opacity disabled:opacity-60"
            style={{ background: "linear-gradient(135deg,#f59e0b 0%,#fbbf24 100%)" }}
          >
            {busy ? "Please wait…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}

"use client";

import { useEffect } from "react";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6 text-center"
      style={{ background: "var(--bg-base)" }}>
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl"
        style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)" }}>
        <svg className="h-6 w-6 text-red-400" viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.3" />
          <path d="M8 5v3.5M8 10.8h.01" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </div>
      <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Something went wrong</p>
      <p className="mt-1 max-w-sm text-xs" style={{ color: "var(--text-muted)" }}>
        The page hit an unexpected error. Your data is safe — try again.
      </p>
      <button type="button" onClick={reset}
        className="mt-5 rounded-lg px-4 py-2 text-xs font-medium transition-colors"
        style={{ background: "rgba(245,158,11,0.10)", border: "1px solid rgba(245,158,11,0.25)", color: "#f59e0b" }}>
        Try again
      </button>
    </div>
  );
}

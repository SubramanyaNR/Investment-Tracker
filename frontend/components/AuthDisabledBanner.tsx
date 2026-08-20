"use client";

import { useEffect, useState } from "react";
import { getAuthStatus } from "@/lib/api";

// Shows whenever AUTH_ENABLED=false on the backend, full stop — no
// local-vs-hosted wording distinction. Deployment topology (Tailscale,
// reverse proxies, etc.) is too ambiguous to word the warning around
// correctly, so it's always the strongest copy. Dismissal is in-memory only
// (resets on reload) — never persisted, so it can't be silenced by accident.
export default function AuthDisabledBanner() {
  const [status, setStatus] = useState<Awaited<ReturnType<typeof getAuthStatus>>>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    getAuthStatus().then(setStatus);
  }, []);

  if (!status || status.auth_enabled || dismissed) return null;

  return (
    <div
      role="alert"
      className="w-full px-4 py-2 text-sm flex items-center justify-between gap-4 border-b bg-red-500/15 border-red-500/30 text-red-200"
    >
      <span>
        <strong>Login is disabled.</strong>{" "}
        Anyone who can reach this address can view and edit your portfolio data.
        Set AUTH_ENABLED=true, run `make reset-admin-password`, and restart if
        that's not acceptable here.
      </span>
      <button
        onClick={() => setDismissed(true)}
        className="shrink-0 opacity-70 hover:opacity-100 transition-opacity"
        aria-label="Dismiss for this session"
      >
        Dismiss
      </button>
    </div>
  );
}

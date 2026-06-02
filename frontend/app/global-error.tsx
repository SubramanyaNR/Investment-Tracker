"use client";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="en" data-theme="dark">
      <body>
        <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", padding: "0 24px", fontFamily: "system-ui, sans-serif", background: "#0a0a0a", color: "#e5e5e5" }}>
          <p style={{ fontSize: 14, fontWeight: 600 }}>Something went wrong</p>
          <p style={{ marginTop: 4, fontSize: 12, color: "#888" }}>The app hit an unexpected error. Your data is safe.</p>
          <button type="button" onClick={reset}
            style={{ marginTop: 20, borderRadius: 8, padding: "8px 16px", fontSize: 12, fontWeight: 500, background: "rgba(245,158,11,0.10)", border: "1px solid rgba(245,158,11,0.25)", color: "#f59e0b", cursor: "pointer" }}>
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}

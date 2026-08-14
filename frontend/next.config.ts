import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // `output: "standalone"` was incompatible with `next start` (how `make frontend`
  // runs it). Re-add it with a `node .next/standalone/server.js` runner when
  // containerising for the VPS.
  turbopack: {
    root: path.resolve(__dirname),
  },
  // Proxy browser API calls (same-origin /api) to the backend. Not user-facing like
  // NEXT_PUBLIC_*, but Next.js still resolves rewrites() destinations at `next build` time
  // (baked into routes-manifest.json, not re-read by `next start`) — so BACKEND_INTERNAL_URL
  // must be set as a build-time env var, not a runtime one. Docker Compose passes it as a build
  // ARG (http://backend:8000, since 127.0.0.1 inside the frontend container is itself, not a
  // separate backend container). Bare-metal (same host, no Docker) keeps the 127.0.0.1 default.
  async rewrites() {
    const backendOrigin = process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000";
    return [
      { source: "/api/:path*", destination: `${backendOrigin}/:path*` },
    ];
  },
};

export default nextConfig;

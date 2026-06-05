import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // `output: "standalone"` was incompatible with `next start` (how `make frontend`
  // runs it). Re-add it with a `node .next/standalone/server.js` runner when
  // containerising for the VPS.
  turbopack: {
    root: path.resolve(__dirname),
  },
  // Proxy browser API calls (same-origin /api) to the backend on this host,
  // so the app works from any client without baking a host IP into the build.
  async rewrites() {
    return [
      { source: "/api/:path*", destination: "http://127.0.0.1:8000/:path*" },
    ];
  },
};

export default nextConfig;

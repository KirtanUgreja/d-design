import type { NextConfig } from "next";

// The e2e run builds into its own folder, so it can never replace the files
// under a server someone is already looking at (2026-10-05).
// /api/* goes to the Python API (api/app.py); the web app has no backend of its own.
const API = process.env.API_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  // A rewrite must not gzip the event stream into one buffered blob.
  compress: false,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
};

export default nextConfig;

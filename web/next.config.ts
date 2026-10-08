import type { NextConfig } from "next";

// The e2e run builds into its own folder, so it can never replace the files
// under a server someone is already looking at (2026-10-05).
// /api/* goes to the Python API (api/app.py) through app/api/[...path]/route.ts,
// which adds the signed-in user's token; Better Auth answers /api/auth/*.
const nextConfig: NextConfig = {
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  // Gzip would buffer the deck's event stream into one blob.
  compress: false,
};

export default nextConfig;

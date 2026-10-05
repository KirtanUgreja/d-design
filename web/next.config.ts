import type { NextConfig } from "next";

// The e2e run builds into its own folder, so it can never replace the files
// under a server someone is already looking at (2026-10-05).
const nextConfig: NextConfig = {
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
};

export default nextConfig;

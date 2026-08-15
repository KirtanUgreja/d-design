/**
 * Next.js config — the editor app (phase 12).
 *
 * Minimal: no plugins. The pure renderer and design tokens in web/src/features
 * are shared with the render package's esbuild bundling, which is untouched by
 * Next. The editor is a client app wrapping the renderer (patterns.md rule 2).
 */
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
};

export default nextConfig;

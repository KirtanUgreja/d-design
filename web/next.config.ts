import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Stable in 16. Hot path #3 is the editor canvas, and the compiler's
  // memoization is worth more there than anywhere else in the product — which
  // is also why the react-hooks lint rules are not optional: a violation
  // silently costs you the memoization rather than failing loudly.
  reactCompiler: true,

  // Author against `use cache` from the start rather than retrofitting it.
  cacheComponents: true,
};

export default nextConfig;

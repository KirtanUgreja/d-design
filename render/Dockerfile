# The render service (phase 18) — "one endpoint, in a validated Deck plus a
# DesignFamily, out HTML" (backend.md). No database, no model credentials, no
# auth. The bundle is server.cjs (built by scripts/build.mjs, which keeps
# Playwright OUT of it — the CVE-rich dependency lives only in the CLI).
#
# Build context is the REPO ROOT (docker-compose: context: .) because render
# bundles web/src via the @web alias — the bundle needs both trees AND web's
# node_modules (the @web/features/* imports resolve react from web/).
FROM node:22-slim

WORKDIR /app

COPY render/package.json render/pnpm-lock.yaml render/pnpm-workspace.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

# The bundle imports web/src, which imports react etc. from web's own
# node_modules — install web too so the esbuild bundle resolves them.
COPY web/package.json web/pnpm-lock.yaml web/pnpm-workspace.yaml ../web/
RUN corepack enable && pnpm --dir ../web install --frozen-lockfile

COPY render/scripts ./scripts
COPY render/src ./src
COPY web/src ../web/src
COPY render/tsconfig.json ./

RUN pnpm exec node scripts/build.mjs

EXPOSE 8001

CMD ["node", "dist/server.cjs"]

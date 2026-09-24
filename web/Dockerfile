# The web app — the editor, auth, and the server-side surface that fronts api.
#
# Built for `output: 'standalone'` (next.config.ts), so the runtime stage gets
# the traced server plus the dependencies it actually imports, not a
# node_modules install. Three stages because the build toolchain has no
# business in the image that runs.
#
# No secrets at build time: every route that touches the database or a session
# is force-dynamic, so the build never needs a live DB or a session cookie.
FROM node:22-slim AS deps
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

FROM node:22-slim AS builder
WORKDIR /app
RUN corepack enable
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN pnpm build

FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
# standalone ships server.js and the traced modules; static is served from
# .next/static beside it.
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]

# The screenshot and measurement service.
#
# **Two stages, because the bundle is built here rather than on a laptop.** The
# first version copied `render/dist` straight in — and `dist/` is gitignored, so
# the image only built for someone who happened to have run `pnpm build` first.
# An image with an undeclared dependency on the host that built it is not
# reproducible; it is a machine's local state wearing a container.
#
# The tag must match the `playwright` version in the lockfile. A client talking
# to browsers it did not ship is the failure that presents as flakiness, and the
# first version of this file pinned v1.56.0 against a lockfile resolving 1.62.1
# — the mismatch this very comment warns about, written and then made two lines
# later.
FROM mcr.microsoft.com/playwright:v1.62.1-noble AS build

WORKDIR /build
ENV CI=true

# The workspace manifests first, so a source-only change reuses the install
# layer. pnpm comes from corepack, which ships with the Node in this image.
RUN corepack enable
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json ./
COPY web/package.json ./web/package.json
COPY render/package.json ./render/package.json

# `--ignore-scripts`, and it is the stronger posture rather than a workaround.
#
# An install script runs arbitrary code from a package author, which is the
# supply-chain step docs/coderules/dependencies.md spends its longest section
# on. This stage needs exactly one thing to work — esbuild — and esbuild's
# platform binary arrives as an optional *dependency* (`@esbuild/linux-*`), not
# as a postinstall download, so it does not need one. The other two scripts
# pnpm would run here belong to `sharp` and `unrs-resolver`, which are Next's
# image pipeline and eslint's resolver: neither is reachable from a bundle of
# the renderer.
#
# If esbuild ever does need its script, this fails loudly at the bundle step
# below rather than shipping a broken image — which is the right way round.
RUN pnpm install --frozen-lockfile --ignore-scripts

# `web/src` is not incidental — it is the renderer. esbuild resolves `@/`
# against it, which is what lets this service run the same component `web`
# ships rather than a copy of it.
COPY web/src ./web/src
COPY web/tsconfig.json ./web/tsconfig.json
COPY render ./render
RUN pnpm --filter @d-design/render build

# --- runtime ---------------------------------------------------------------
FROM mcr.microsoft.com/playwright:v1.62.1-noble

WORKDIR /srv
ENV NODE_ENV=production

# Only the externals the bundle did not inline: playwright, react, react-dom
# and the four font packages `fonts.ts` reads woff2 from at runtime. No
# toolchain, no source, no pnpm.
COPY render/package.json ./package.json
RUN npm install --omit=dev --no-audit --no-fund && npm cache clean --force

COPY --from=build /build/render/dist ./dist

# `pwuser` ships with the image and is not root. Running as root is how a
# container ends up needing `--no-sandbox`, which is the one change that would
# make running a browser here dangerous (docs/security/testing.md -> "Chromium
# runs sandboxed").
USER pwuser

EXPOSE 3200

# Node, not curl: the image has no curl, and installing one for the benefit of
# a health probe is a package added to watch a package.
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
  CMD node -e "fetch('http://127.0.0.1:3200/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "dist/server.js"]

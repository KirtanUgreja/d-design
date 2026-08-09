# Playwright's own image, pinned to the version in package.json. The browser
# binaries and every system library they need are already in it, and matching
# the tags is not optional — a Playwright client talking to browsers it did not
# ship is the failure that looks like a flaky test.
FROM mcr.microsoft.com/playwright:v1.56.0-noble

WORKDIR /srv

# The bundle is self-contained apart from the externals in build.mjs, so the
# image installs those and nothing else — no source, no toolchain, no pnpm.
COPY render/package.json ./package.json
RUN npm install --omit=dev --no-audit --no-fund

COPY render/dist ./dist

# `pwuser` ships with the image and is not root. Running as root is how a
# container ends up needing `--no-sandbox`, which is the single change that
# would make a browser here dangerous (docs/security/testing.md -> "Chromium
# runs sandboxed").
USER pwuser

ENV NODE_ENV=production
EXPOSE 3200

# No HEALTHCHECK curl: the image has no curl, and adding one to run a health
# probe is a package installed for the benefit of the probe. Compose asks Node,
# which is already here.
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
  CMD node -e "fetch('http://127.0.0.1:3200/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "dist/server.js"]

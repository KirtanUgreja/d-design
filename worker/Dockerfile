# The upload worker — the isolated process with nothing to steal. Built from
# its own package; runs the HTTP ingest endpoint on 8080.
FROM node:22-slim

WORKDIR /app

# sharp needs libvips native bits on slim images.
RUN apt-get update && apt-get install -y --no-install-recommends libvips-dev \
  && rm -rf /var/lib/apt/lists/*

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

COPY tsconfig.json ./
COPY src ./src

EXPOSE 8080

CMD ["pnpm", "exec", "tsx", "src/index.ts"]

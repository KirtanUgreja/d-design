# The web service: the only public one. Next.js and Better Auth; it reaches
# the API over Railway's private network (API_ORIGIN).
FROM node:22-slim
RUN corepack enable
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build
ENV NODE_ENV=production
CMD ["sh", "-c", "exec pnpm start -p ${PORT:-3000} -H 0.0.0.0"]

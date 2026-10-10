# The web service: the only public one. Next.js and Better Auth; it reaches
# the API over Railway's private network (API_ORIGIN).
FROM public.ecr.aws/docker/library/node:22-slim
RUN corepack enable
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build
ENV NODE_ENV=production
# AUTH_MIGRATE=1 (set by scripts/deploy-railway.sh) creates Better Auth's
# tables before serving; it is a no-op once they exist.
CMD ["sh", "-c", "if [ \"$AUTH_MIGRATE\" = 1 ]; then pnpm dlx auth@1.7.7 migrate --config lib/auth.ts --yes; fi && exec pnpm start -p ${PORT:-3000} -H 0.0.0.0"]

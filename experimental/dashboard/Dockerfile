FROM node:24-alpine AS base
# Pin pnpm to the major version that produced pnpm-lock.yaml (matches
# `packageManager` field in root package.json). Without this pin,
# `npm install -g pnpm` installs the latest (10.x) and fails against
# a 9.x-format lockfile.
RUN npm install -g pnpm@9

# ── deps ──────────────────────────────────────────────────────────────────────
FROM base AS deps
WORKDIR /app
# Copy workspace config + lockfile + every workspace member's package.json.
# pnpm install --frozen-lockfile validates the lockfile against the full set of
# workspace packages. Missing any member's package.json causes pnpm to install a
# partial dep tree, which surfaces as cryptic "Failed to install required
# TypeScript dependencies" / "different major version of pnpm" errors at build
# time. Keep this list in sync with pnpm-workspace.yaml.
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json ./
COPY adapters/mcp/package.json ./adapters/mcp/
COPY apps/dashboard/package.json ./apps/dashboard/
COPY sdks/stigmem-ts/package.json ./sdks/stigmem-ts/
RUN pnpm install --frozen-lockfile

# ── builder ───────────────────────────────────────────────────────────────────
FROM base AS builder
WORKDIR /app

# NEXT_PUBLIC_STIGMEM_API_URL must be set at build time for client-side React Query
ARG NEXT_PUBLIC_STIGMEM_API_URL
ENV NEXT_PUBLIC_STIGMEM_API_URL=${NEXT_PUBLIC_STIGMEM_API_URL}

COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/dashboard/node_modules ./apps/dashboard/node_modules
COPY . .
RUN pnpm --filter dashboard build

# ── runner ────────────────────────────────────────────────────────────────────
FROM node:24-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/apps/dashboard/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/dashboard/.next/static ./apps/dashboard/.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "apps/dashboard/server.js"]

FROM node:22-alpine AS dependencies

WORKDIR /app
COPY package.json yarn.lock .yarnrc.yml ./
RUN corepack enable && yarn install --immutable

FROM node:22-alpine AS builder

WORKDIR /app
ARG BACKEND_URL=http://api:8000
ARG NEXT_PUBLIC_GOOGLE_CLIENT_ID
ENV BACKEND_URL=$BACKEND_URL \
    NEXT_PUBLIC_GOOGLE_CLIENT_ID=$NEXT_PUBLIC_GOOGLE_CLIENT_ID \
    NEXT_TELEMETRY_DISABLED=1

COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
RUN corepack enable && yarn build

FROM node:22-alpine AS runner

WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 3000

CMD ["node", "server.js"]

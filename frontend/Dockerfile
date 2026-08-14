FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG NEXT_PUBLIC_API_BASE_URL=/api
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
# next.config.ts's rewrites() destination is resolved at build time (baked into
# routes-manifest.json, not re-read at `next start`), so this must be a build ARG too.
ARG BACKEND_INTERNAL_URL=http://127.0.0.1:8000
ENV BACKEND_INTERNAL_URL=$BACKEND_INTERNAL_URL
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/next.config.ts ./next.config.ts
EXPOSE 3000
ENV PORT=3000
CMD ["npm", "start"]

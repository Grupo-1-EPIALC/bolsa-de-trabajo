# syntax=docker/dockerfile:1
# ------------------------------------------------------------------- deps ---
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# -------------------------------------------------------------------- dev ---
FROM deps AS dev
COPY . .
EXPOSE 3000
CMD ["npm", "run", "start:dev"]

# ------------------------------------------------------------------ build ---
FROM deps AS build
COPY . .
RUN npm run build && npm prune --omit=dev

# ---------------------------------------------------------------- runtime ---
FROM node:22-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /app
COPY --from=build --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/dist ./dist
COPY --chown=node:node package.json ./
USER node
EXPOSE 3000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1:3000/health > /dev/null || exit 1
CMD ["node", "dist/main.js"]

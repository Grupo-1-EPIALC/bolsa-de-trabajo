# syntax=docker/dockerfile:1
# ------------------------------------------------------------------- deps ---
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# -------------------------------------------------------------------- dev ---
FROM deps AS dev
COPY . .
EXPOSE 8080
CMD ["npm", "run", "dev"]

# ------------------------------------------------------------------ build ---
FROM deps AS build
COPY . .
RUN npm run build

# ---------------------------------------------------------------- runtime ---
FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/ > /dev/null || exit 1

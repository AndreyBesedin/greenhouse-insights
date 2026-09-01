# Build stage: compiles the SPA. VITE_API_BASE_URL is baked into the JS
# bundle at build time (Vite env vars are compile-time), so pointing this
# image at a different backend means rebuilding it with a different
# --build-arg, not changing a runtime environment variable.
FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
# --legacy-peer-deps: openapi-typescript wants typescript@^5.x while this
# project pins ~6.0.2; a known, pre-existing peer conflict, not something
# this image introduces.
RUN npm ci --legacy-peer-deps

COPY . .
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# Runtime stage: static files behind nginx, with SPA fallback so client-side
# routes (e.g. /greenhouses/gh_001) resolve to index.html instead of 404ing.
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80

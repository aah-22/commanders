# Build the Angular app, then serve it from nginx-unprivileged (non-root, port 8080). Coolify strips `ports:`;
# the tunnel targets this container's internal IP:8080.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build -- --configuration production

FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY nginx/security-headers.conf /etc/nginx/security-headers.conf
COPY --from=build /app/dist/web/browser /usr/share/nginx/html
USER nginx
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1

# Multi-stage build for Nuvorix Web Platform Console
FROM node:22-slim AS builder

WORKDIR /app

COPY apps/web/package.json ./
RUN npm install --legacy-peer-deps

COPY apps/web/ ./
RUN npm run build

# Nginx production server
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

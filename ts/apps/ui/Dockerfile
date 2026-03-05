# -- Stage 1: Build --
FROM node:20-alpine AS builder
WORKDIR /app

# Accept build-time env vars (azd passes these from `azd env`)
ARG VITE_BACKEND_URL=http://localhost:8000
ARG VITE_AUTH_MODE=dev
ARG VITE_APP_INSIGHTS_TRACE_URL=""
ARG VITE_CONTOSO_WEB_CLIENT_ID=""
ARG VITE_CONTOSO_TENANT_ID=""
ARG VITE_CONTOSO_API_SCOPE=""

# Expose to Vite's build process
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL
ENV VITE_AUTH_MODE=$VITE_AUTH_MODE
ENV VITE_APP_INSIGHTS_TRACE_URL=$VITE_APP_INSIGHTS_TRACE_URL
ENV VITE_CONTOSO_WEB_CLIENT_ID=$VITE_CONTOSO_WEB_CLIENT_ID
ENV VITE_CONTOSO_TENANT_ID=$VITE_CONTOSO_TENANT_ID
ENV VITE_CONTOSO_API_SCOPE=$VITE_CONTOSO_API_SCOPE

RUN corepack enable && corepack prepare pnpm@latest --activate

COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

# -- Stage 2: Serve --
FROM nginx:alpine AS runner
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

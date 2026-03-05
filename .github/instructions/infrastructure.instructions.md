---
applyTo: "infra/**,**/*.bicep,**/Dockerfile,**/docker-compose*.yml"
---

# Infrastructure Instructions

These instructions apply to infrastructure files (Docker, Terraform, deployment configs).

## Docker Best Practices

### Multi-Stage Builds
```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

# Production stage
FROM nginx:alpine AS runner
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

### Security Rules
- Use specific image tags (not `latest`)
- Run as non-root user
- Minimize installed packages
- Never copy secrets into images
- Never hardcode credentials

## Terraform Best Practices

### File Organization
- `main.tf` -- providers and all resources
- `variables.tf` -- all input variables with descriptions
- `outputs.tf` -- all outputs needed for env file generation
- Use a `prefix` variable for consistent resource naming
- Tag all resources with `project`, `environment`

### Naming Convention
```hcl
variable "prefix" {
  description = "Resource name prefix"
  default     = "contoso-conv-router"
}

resource "azurerm_resource_group" "main" {
  name     = "${var.prefix}-rg"
  location = var.location
  tags     = var.tags
}
```

### Security Requirements
- Cosmos DB: private endpoint only, public access disabled
- ACA Environment: VNet-injected
- Backend: User-Assigned Managed Identity for Cosmos access
- All secrets via environment variables, never in Terraform state

## Azure Container Apps

### Health Probes
- Backend: `GET /healthz`
- Frontend: `GET /`

### Resource Limits
| Service | CPU | Memory | Min Replicas | Max Replicas |
|---------|-----|--------|--------------|--------------|
| Frontend | 0.25 | 0.5Gi | 1 | 3 |
| Backend | 0.5 | 1Gi | 1 | 5 |

## Environment Variables

- Use `.env.example` for templates (committed)
- Document all required variables
- Never commit actual `.env` files
- Never put secrets in Dockerfiles

# AWS App Runner Deploy Guide

Deploy stigmem to [AWS App Runner](https://aws.amazon.com/apprunner/) — fully
managed, auto-scaling, no cluster management.

## Prerequisites

- AWS account with App Runner permissions
- AWS CLI v2 installed and configured (`aws configure`)
- Docker (to push the image to ECR)

## Steps

### 1. Build and push the image to ECR

```bash
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/stigmem-node

# Create ECR repository (once)
aws ecr create-repository --repository-name stigmem-node --region $AWS_REGION

# Login, build, push (from repo root)
aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker build -f node/Dockerfile -t stigmem-node:latest .
docker tag stigmem-node:latest "$ECR_REPO:latest"
docker push "$ECR_REPO:latest"
```

### 2. Store secrets in AWS Secrets Manager

```bash
aws secretsmanager create-secret \
  --name stigmem/env \
  --secret-string '{
    "STIGMEM_LIBSQL_AUTH_TOKEN": "<TOKEN>",
    "STIGMEM_OIDC_ISSUER_URL": "<IDP_ISSUER>",
    "STIGMEM_OIDC_AUDIENCE": "<CLIENT_ID>"
  }'
```

### 3. Create the App Runner service (console)

1. **AWS Console → App Runner → Create service**
2. **Source**: Container registry → Amazon ECR
3. **Image URI**: `<account>.dkr.ecr.<region>.amazonaws.com/stigmem-node:latest`
4. **Port**: `8765`
5. **Environment variables**:

| Key | Value |
|---|---|
| `STIGMEM_PORT` | `8765` |
| `STIGMEM_NODE_URL` | _(fill in after first deploy)_ |
| `STIGMEM_LOG_LEVEL` | `info` |
| `STIGMEM_AUTH_REQUIRED` | `true` |
| `STIGMEM_STORAGE_BACKEND` | `libsql` |
| `STIGMEM_LIBSQL_URL` | `libsql://<DB>.turso.io` |
| `STIGMEM_LIBSQL_AUTH_TOKEN` | _(from Secrets Manager)_ |

6. **Health check**: Path `/healthz`, Port `8765`, Interval 10s
7. Click **Create and deploy**

After deploy, copy the **Default domain** URL and update `STIGMEM_NODE_URL`.

### 4. Verify

```bash
curl https://<apprunner-domain>/healthz
```

## SQLite + EFS (persistent volume)

App Runner supports EFS mounts for persistent SQLite:

1. Create an EFS file system in the same VPC
2. Enable **VPC connector** on the App Runner service
3. Add an EFS volume mount to the service config:
   - **Mount point**: `/data`
4. Set `STIGMEM_DB_PATH=/data/stigmem.db` and `STIGMEM_STORAGE_BACKEND=sqlite`

This is more complex than Turso; the libSQL backend is recommended for App Runner.

## Auto-scaling

App Runner auto-scales based on request concurrency.
Tune in **Service → Configuration → Auto scaling**:
- Min instances: 1 (avoid cold start)
- Max instances: depends on workload
- Concurrency: 100 (default)

## OIDC auth

Set in environment (or Secrets Manager):
- `STIGMEM_OIDC_ENABLED=true`
- `STIGMEM_OIDC_ISSUER_URL=<IDP_ISSUER>`
- `STIGMEM_OIDC_AUDIENCE=<CLIENT_ID>`
- `STIGMEM_OIDC_ALLOWED_DOMAINS=example.com`

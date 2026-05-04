# GCP Cloud Run Deploy Guide

Deploy stigmem to [Google Cloud Run](https://cloud.google.com/run) — scale-to-zero
serverless containers with optional persistent storage.

## Prerequisites

- GCP project with billing enabled
- `gcloud` CLI installed and authenticated (`gcloud auth login`)
- Docker (to push to Artifact Registry)

## Steps

### 1. Set up Artifact Registry and push the image

```bash
PROJECT_ID=$(gcloud config get-value project)
REGION=us-central1
REPO=stigmem

# Create Artifact Registry repo (once)
gcloud artifacts repositories create "$REPO" \
  --repository-format docker \
  --location "$REGION"

# Configure Docker auth
gcloud auth configure-docker "$REGION-docker.pkg.dev"

# Build and push (from repo root)
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/stigmem-node:latest"
docker build -f node/Dockerfile -t "$IMAGE" .
docker push "$IMAGE"
```

### 2. Store secrets in Secret Manager

```bash
printf '<TURSO_AUTH_TOKEN>' \
  | gcloud secrets create stigmem-libsql-token --data-file=-

# Or for OIDC:
printf '<OIDC_CLIENT_SECRET>' \
  | gcloud secrets create stigmem-oidc-secret --data-file=-
```

Grant the Cloud Run service account access:
```bash
SA_EMAIL="$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')-compute@developer.gserviceaccount.com"
gcloud secrets add-iam-policy-binding stigmem-libsql-token \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"
```

### 3. Deploy to Cloud Run

```bash
gcloud run deploy stigmem \
  --image "$IMAGE" \
  --region "$REGION" \
  --port 8765 \
  --allow-unauthenticated \
  --set-env-vars "STIGMEM_PORT=8765,STIGMEM_LOG_LEVEL=info,STIGMEM_STORAGE_BACKEND=libsql,STIGMEM_LIBSQL_URL=libsql://<DB>.turso.io" \
  --set-secrets "STIGMEM_LIBSQL_AUTH_TOKEN=stigmem-libsql-token:latest" \
  --min-instances 0 \
  --max-instances 10
```

After deploy, get the URL:
```bash
SERVICE_URL=$(gcloud run services describe stigmem --region "$REGION" \
  --format 'value(status.url)')
echo "$SERVICE_URL"
curl "$SERVICE_URL/healthz"
```

Update `STIGMEM_NODE_URL`:
```bash
gcloud run services update stigmem --region "$REGION" \
  --set-env-vars "STIGMEM_NODE_URL=$SERVICE_URL"
```

## SQLite + Cloud Filestore (persistent volume)

Cloud Run supports NFS mounts for persistent SQLite:

1. Create a Filestore instance in the same VPC
2. Add a volume mount to the Cloud Run service:

```bash
gcloud run services update stigmem --region "$REGION" \
  --add-volume "name=stigmem-data,type=nfs,location=<FILESTORE_IP>,readonly=false,path=/stigmem" \
  --add-volume-mount "volume=stigmem-data,mount-path=/data" \
  --set-env-vars "STIGMEM_STORAGE_BACKEND=sqlite,STIGMEM_DB_PATH=/data/stigmem.db"
```

NFS adds latency; the libSQL/Turso backend is recommended for scale-to-zero workloads.

## OIDC auth

```bash
gcloud run services update stigmem --region "$REGION" \
  --set-env-vars "STIGMEM_AUTH_REQUIRED=true,STIGMEM_OIDC_ENABLED=true,STIGMEM_OIDC_ISSUER_URL=<IDP_ISSUER>,STIGMEM_OIDC_AUDIENCE=<CLIENT_ID>,STIGMEM_OIDC_ALLOWED_DOMAINS=example.com"
```

## Scale to zero

`--min-instances 0` (the default) means idle instances stop.
Cold start is ~300–800 ms. Set `--min-instances 1` to eliminate cold starts.

## Health check

Cloud Run uses the startup probe and HTTP health check automatically on the
configured port. No extra configuration needed; `/healthz` responds with 200.

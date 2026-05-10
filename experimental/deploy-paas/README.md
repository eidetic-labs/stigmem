# PaaS Deploy Recipes

Quick-start guides for popular managed container platforms.

| Platform | Guide | Notes |
|---|---|---|
| [Render](./render.md) | render.md | Free tier available; persistent disk add-on |
| [Railway](./railway.md) | railway.md | Simple GitHub-connected deploys |
| [AWS App Runner](./aws-app-runner.md) | aws-app-runner.md | Auto-scaling; IAM-native secrets |
| [GCP Cloud Run](./gcp-cloud-run.md) | gcp-cloud-run.md | Scale-to-zero; Cloud SQL or Filestore for persistence |

## Common notes across all PaaS platforms

- **Persistence**: PaaS containers are ephemeral. For SQLite, mount a persistent
  volume (Render Disk, EFS, Filestore, etc.) at `/data`. For stateless deploys,
  use the **libSQL / Turso** backend (`STIGMEM_STORAGE_BACKEND=libsql`).
- **Secrets**: Never hard-code secrets in config files or environment variable
  values checked into git. Use the platform's secrets manager.
- **Node URL**: Set `STIGMEM_NODE_URL` to the public HTTPS URL assigned by the
  platform after the first deploy.
- **Port**: The node listens on `8765` by default. Most platforms map this
  automatically; consult your platform's docs if it expects `PORT` instead.

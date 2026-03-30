# Deploying JuntosHQ on Google Cloud

JuntosHQ is a Python/Flask WSGI application backed by **Supabase** (PostgreSQL + pgvector).  
This document compares four Google Cloud hosting options and provides a Cloud Run quick-start.

---

## Contents

1. [Option comparison](#option-comparison)
2. [Cloud Run (recommended)](#cloud-run-recommended)
3. [App Engine Flexible](#app-engine-flexible)
4. [Google Kubernetes Engine (GKE) Autopilot](#google-kubernetes-engine-gke-autopilot)
5. [Compute Engine](#compute-engine)
6. [Supabase connection notes](#supabase-connection-notes)
7. [Required environment variables](#required-environment-variables)
8. [CI/CD with Cloud Build](#cicd-with-cloud-build)
9. [Updating an already-running service](#updating-an-already-running-service)

---

## Option comparison

| | **Cloud Run** | **App Engine Flexible** | **GKE Autopilot** | **Compute Engine** |
|---|---|---|---|---|
| **Type** | Serverless containers | Managed PaaS (Docker) | Managed Kubernetes | Virtual machines |
| **Effort to deploy** | Low | Low–Medium | High | High |
| **Scales to zero** | ✅ Yes | ❌ No (min 1 instance) | ❌ No | ❌ No |
| **Cold-start latency** | ~1–3 s (min-instances=0) | N/A | N/A | N/A |
| **Cost at low traffic** | Near-zero (pay per request) | ~$30–60/mo minimum | ~$50+/mo minimum | ~$15–50/mo minimum |
| **Cost at high traffic** | Scales up automatically | Scales up automatically | Scales up automatically | Manual scaling |
| **Custom domain + HTTPS** | Built-in | Built-in | Ingress required | Manual (nginx/cert) |
| **Secrets management** | Secret Manager native | Secret Manager | Secret Manager | Secret Manager / env |
| **Docker required** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ Optional |
| **Best for** | Most Flask SaaS apps | Teams already on GAE | Large-scale / microservices | Full infra control |

**Recommendation:** Start with **Cloud Run**.  It requires the least operational overhead, costs nothing when idle, and integrates natively with Secret Manager and Cloud Build.

---

## Cloud Run (recommended)

Cloud Run runs stateless containers.  Each request is routed to a container instance; instances are created or torn down automatically based on traffic.

### Why it fits JuntosHQ

- **No persistent local state** — all state lives in Supabase (PostgreSQL) and in the signed session cookie.
- **AI API calls are I/O-bound** — gunicorn workers spend most time waiting for Anthropic / Voyage AI responses; Cloud Run handles this well.
- **Variable traffic** — scales to zero overnight and scales up instantly for bursts.

### Prerequisites

```bash
# Install and authenticate the gcloud CLI
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com
```

### Step 1 — Create an Artifact Registry repository

```bash
gcloud artifacts repositories create juntoshq \
  --repository-format=docker \
  --location=us-west1 \
  --description="JuntosHQ container images"
```

### Step 2 — Store secrets in Secret Manager

Never put secrets in environment variable flags that appear in shell history or Cloud Run revision annotations.  Use Secret Manager instead.

```bash
# Database URL from your Supabase project settings → Database → Connection string
#   Use the "URI" format: postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
echo -n "postgresql://..." | \
  gcloud secrets create DATABASE_URL --data-file=-

# Flask session signing key — generate a strong random value
python3 -c "import secrets; print(secrets.token_hex(32))" | \
  gcloud secrets create SECRET_KEY --data-file=-

# OAuth credentials (see docs/authentication.md for how to obtain)
echo -n "YOUR_GOOGLE_CLIENT_ID"     | gcloud secrets create GOOGLE_CLIENT_ID     --data-file=-
echo -n "YOUR_GOOGLE_CLIENT_SECRET" | gcloud secrets create GOOGLE_CLIENT_SECRET  --data-file=-
echo -n "YOUR_GITHUB_CLIENT_ID"     | gcloud secrets create GITHUB_CLIENT_ID     --data-file=-
echo -n "YOUR_GITHUB_CLIENT_SECRET" | gcloud secrets create GITHUB_CLIENT_SECRET  --data-file=-

# AI API keys
echo -n "YOUR_ANTHROPIC_API_KEY"    | gcloud secrets create ANTHROPIC_API_KEY     --data-file=-
echo -n "YOUR_VOYAGE_API_KEY"       | gcloud secrets create VOYAGE_API_KEY        --data-file=-

# Stripe (optional — required for billing features)
echo -n "YOUR_STRIPE_SECRET_KEY"        | gcloud secrets create STRIPE_SECRET_KEY       --data-file=-
echo -n "YOUR_STRIPE_WEBHOOK_SECRET"    | gcloud secrets create STRIPE_WEBHOOK_SECRET   --data-file=-
echo -n "price_..."                     | gcloud secrets create STRIPE_PRICE_STANDARD   --data-file=-
echo -n "price_..."                     | gcloud secrets create STRIPE_PRICE_EXPANDED   --data-file=-
echo -n "price_..."                     | gcloud secrets create STRIPE_PRICE_CHATBOT    --data-file=-

# Email / SMTP (optional — required for invite emails)
echo -n "smtp.sendgrid.net"   | gcloud secrets create MAIL_SERVER    --data-file=-
echo -n "587"                  | gcloud secrets create MAIL_PORT      --data-file=-
echo -n "apikey"               | gcloud secrets create MAIL_USERNAME  --data-file=-
echo -n "YOUR_SENDGRID_KEY"    | gcloud secrets create MAIL_PASSWORD  --data-file=-```

### Step 3 — Grant Cloud Run access to secrets

```bash
# Get the Cloud Run default service account email
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)")
CR_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Grant Secret Manager accessor role
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:${CR_SA}" \
  --role="roles/secretmanager.secretAccessor"
```

### Step 4 — Build and push the image

```bash
REGION=us-west1
PROJECT=$(gcloud config get-value project)
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/juntoshq/juntoshq"

# Authenticate Docker with Artifact Registry
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build and push
docker build -t "${IMAGE}:latest" .
docker push "${IMAGE}:latest"
```

### Step 5 — Run database migrations

Run migrations once before deploying traffic. Alembic is safe to run repeatedly (idempotent).

```bash
DB_URL=$(gcloud secrets versions access latest --secret=DATABASE_URL)

docker run --rm \
  -e DATABASE_URL="${DB_URL}" \
  -e SECRET_KEY="placeholder-migration-only" \
  "${IMAGE}:latest" \
  .venv/bin/alembic upgrade head
```

### Step 6 — Deploy to Cloud Run

```bash
gcloud run deploy juntoshq \
  --image="${IMAGE}:latest" \
  --region=us-west1 \
  --platform=managed \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=10 \
  --memory=1Gi \
  --cpu=1 \
  --timeout=300 \
  --set-secrets="DATABASE_URL=DATABASE_URL:latest,\
SECRET_KEY=SECRET_KEY:latest,\
GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest,\
GOOGLE_CLIENT_SECRET=GOOGLE_CLIENT_SECRET:latest,\
GITHUB_CLIENT_ID=GITHUB_CLIENT_ID:latest,\
GITHUB_CLIENT_SECRET=GITHUB_CLIENT_SECRET:latest,\
ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest,\
VOYAGE_API_KEY=VOYAGE_API_KEY:latest,\
STRIPE_SECRET_KEY=STRIPE_SECRET_KEY:latest,\
STRIPE_WEBHOOK_SECRET=STRIPE_WEBHOOK_SECRET:latest,\
STRIPE_PRICE_STANDARD=STRIPE_PRICE_STANDARD:latest,\
STRIPE_PRICE_EXPANDED=STRIPE_PRICE_EXPANDED:latest,\
STRIPE_PRICE_CHATBOT=STRIPE_PRICE_CHATBOT:latest,\
MAIL_SERVER=MAIL_SERVER:latest,\
MAIL_USERNAME=MAIL_USERNAME:latest,\
MAIL_PASSWORD=MAIL_PASSWORD:latest"
```

### Step 7 — Update OAuth redirect URIs

After deploying, note the service URL (e.g. `https://juntoshq-xxxx-uw.a.run.app`).

- **Google Cloud Console** → APIs & Services → Credentials → your OAuth 2.0 client:
  - Add `https://juntoshq-xxxx-uw.a.run.app/auth/callback/google` to Authorized redirect URIs.
- **GitHub Developer Settings** → OAuth Apps → your app:
  - Set Authorization callback URL to `https://juntoshq-xxxx-uw.a.run.app/auth/callback/github`.

### Step 8 — Map a custom domain (optional)

```bash
gcloud run domain-mappings create \
  --service=juntoshq \
  --domain=app.juntoshq.com \
  --region=us-west1
```

Cloud Run provisions a managed TLS certificate automatically.

### Sizing guidance

| Traffic level | `--min-instances` | `--max-instances` | `--memory` | Monthly est. |
|---|---|---|---|---|
| Dev / staging | 0 | 2 | 512Mi | ~$0–5 |
| Low (< 1k req/day) | 0 | 5 | 1Gi | ~$5–20 |
| Medium (< 50k req/day) | 1 | 10 | 1Gi | ~$30–80 |
| High (> 50k req/day) | 2 | 50 | 2Gi | ~$100+ |

Setting `--min-instances=1` eliminates cold starts for production; it adds a small baseline cost (~$15/mo for 1 Gi instance).

---

## App Engine Flexible

App Engine Flexible runs Docker containers on Compute Engine VMs managed by Google.  It is a good choice if your team is already using App Engine Standard and wants an upgrade path, but it does **not** scale to zero.

### `app.yaml`

Create an `app.yaml` file (not committed by default — add your own):

```yaml
runtime: custom
env: flex

resources:
  cpu: 1
  memory_gb: 1.0
  disk_size_gb: 10

automatic_scaling:
  min_num_instances: 1
  max_num_instances: 5
  cool_down_period_sec: 60
  cpu_utilization:
    target_utilization: 0.6

env_variables:
  # Do NOT put secrets here — use Secret Manager and access them at startup
  ANTHROPIC_MODEL: "claude-sonnet-4-5"

beta_settings:
  cloud_sql_instances: ""  # leave blank — connecting to Supabase directly
```

### Deploy

```bash
# Load secrets into environment before deploy
export DATABASE_URL=$(gcloud secrets versions access latest --secret=DATABASE_URL)
# ... repeat for other secrets ...

gcloud app deploy
```

> **Note:** App Engine Flexible starts billing immediately (even at zero traffic) because it always keeps at least one VM alive.

---

## Google Kubernetes Engine (GKE) Autopilot

GKE Autopilot manages node pools automatically.  Choose this path when you need:
- Multiple microservices or workers (e.g. a separate Celery worker).
- Advanced networking (VPC, private cluster, multi-region).
- More granular resource controls than Cloud Run offers.

### When to consider it

- Your team is already familiar with Kubernetes.
- You need sidecars (e.g. a Cloud SQL Auth Proxy, though JuntosHQ connects directly to Supabase).
- You require persistent volumes for local model weights (sentence-transformers).

### Quick overview

```bash
# Create an Autopilot cluster
gcloud container clusters create-auto juntoshq-cluster \
  --region=us-central1

# Get credentials
gcloud container clusters get-credentials juntoshq-cluster --region=us-central1

# Apply a Kubernetes deployment (create your own deployment.yaml)
kubectl apply -f k8s/
```

A minimal `k8s/deployment.yaml` would reference the same Docker image built for Cloud Run, with secrets sourced from Kubernetes Secrets (ideally backed by Secret Manager via the External Secrets Operator).

GKE Autopilot is considerably more complex and expensive than Cloud Run for a monolithic Flask application.  Revisit this option when you outgrow Cloud Run's 10-instance default cap or need persistent volumes.

---

## Compute Engine

Compute Engine gives you full control of a Linux VM.  This approach is most familiar to developers coming from traditional VPS hosting (DigitalOcean, Linode, etc.).

### When to use it

- You need a persistent local filesystem (large model weights stored on disk).
- You require custom kernel modules or GPU access (e.g. running sentence-transformers inference locally rather than via Voyage AI).
- Budget-sensitive workloads where you want a fixed monthly cost with no per-request charges.

### Quick overview

```bash
# Create an e2-small VM (2 vCPU, 2 GB RAM) — adjust as needed
gcloud compute instances create juntoshq-vm \
  --machine-type=e2-small \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --tags=http-server,https-server \
  --zone=us-central1-a

# SSH in
gcloud compute ssh juntoshq-vm --zone=us-central1-a
```

On the VM:
```bash
# Install Python 3.12, uv, nginx, certbot
sudo apt-get update && sudo apt-get install -y python3.12 python3-pip nginx certbot python3-certbot-nginx
pip install uv

# Clone your repo, set up .env, run migrations, start gunicorn
# Use systemd to manage the gunicorn process
# Use nginx as a reverse proxy handling TLS
```

Compute Engine requires the most manual management (OS patching, TLS renewal, process supervision) but offers the most flexibility.

---

## Supabase connection notes

JuntosHQ connects to Supabase as a standard PostgreSQL database.  No Supabase-specific SDK is required.

### Connection string format

In the Supabase dashboard → Project Settings → Database → Connection string, select **URI** and copy the connection string.  It looks like:

```
postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
```

Set this as the `DATABASE_URL` secret.  The `_normalize_db_url()` function in `src/juntos/config.py` rewrites `postgres://` → `postgresql+psycopg://` automatically.

### pgvector

Supabase includes the `pgvector` extension by default.  Ensure it is enabled in your Supabase project:

```sql
-- Run once in the Supabase SQL editor
CREATE EXTENSION IF NOT EXISTS vector;
```

The `franklin_passages` table (used by Ben's Counsel RAG) stores `vector(1024)` embeddings.  After deploying and running migrations, seed the corpus once:

```bash
# From a Cloud Run Job, local machine, or Cloud Shell
DATABASE_URL="..." python scripts/seed_franklin.py
```

### Connection pooling

For Cloud Run (which can scale to many concurrent instances), use the **Transaction pooler** connection string from Supabase (port 6543) rather than the direct connection (port 5432).  Transaction pooling is safe with SQLAlchemy because each request uses a short-lived transaction.

---

## Required environment variables

See [Configuration](configuration.md) for the complete reference.  The minimum set for a production Cloud Run deployment:

| Secret Manager key | Purpose | Required |
|---|---|---|
| `DATABASE_URL` | Supabase PostgreSQL URI | ✅ |
| `SECRET_KEY` | Flask session signing | ✅ |
| `GOOGLE_CLIENT_ID` | Google OAuth | ✅ (if using Google login) |
| `GOOGLE_CLIENT_SECRET` | Google OAuth | ✅ (if using Google login) |
| `GITHUB_CLIENT_ID` | GitHub OAuth | ✅ (if using GitHub login) |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth | ✅ (if using GitHub login) |
| `ANTHROPIC_API_KEY` | Ben's Counsel chatbot | ✅ (if using chatbot) |
| `VOYAGE_API_KEY` | RAG embeddings (Franklin passages) | ✅ (if using chatbot) |
| `STRIPE_SECRET_KEY` | Billing | Optional |
| `STRIPE_WEBHOOK_SECRET` | Billing webhooks | Optional |
| `STRIPE_PRICE_STANDARD` | Standard plan Stripe price ID | Optional |
| `STRIPE_PRICE_EXPANDED` | Expanded plan Stripe price ID | Optional |
| `STRIPE_PRICE_CHATBOT` | Chatbot add-on Stripe price ID | Optional |
| `MAIL_SERVER` | SMTP host for invite emails | Optional |
| `MAIL_USERNAME` | SMTP username | Optional |
| `MAIL_PASSWORD` | SMTP password | Optional |

---

## CI/CD with Cloud Build

The repository includes `cloudbuild.yaml` which automates:

1. **Build** — `docker build` the application image.
2. **Push** — push to Artifact Registry tagged with the commit SHA and `latest`.
3. **Migrate** — run `alembic upgrade head` against Supabase before cutting traffic.
4. **Deploy** — `gcloud run deploy` the new image to Cloud Run.

### Wire it to GitHub

```bash
# One-time setup: connect your GitHub repo to Cloud Build
gcloud builds triggers create github \
  --repo-name=JuntosHQ \
  --repo-owner=YOUR_GITHUB_USERNAME \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --region=us-west1
```

### Grant Cloud Build permissions

```bash
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format="value(projectNumber)")
CB_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/artifactregistry.writer"
```

After this, every push to `main` will trigger a build, migration run, and Cloud Run deployment automatically.

---

## Updating an already-running service

If the Cloud Run service is already deployed but **OAuth login fails with "Missing required parameter: client_id"**, it means the secrets were never injected into the running service (e.g. the original deploy skipped `--set-secrets`, or secrets don't yet exist in Secret Manager).

### One-command fix

The `scripts/setup-secrets.sh` helper reads your local `.env` file, creates or updates each secret in Secret Manager, grants the Cloud Run service account access, and then calls `gcloud run services update` to inject everything into the live service — no rebuild required.

```bash
# From the repo root, with gcloud authenticated and your .env file present:
./scripts/setup-secrets.sh

# Or specify project/region/service explicitly:
./scripts/setup-secrets.sh -p YOUR_PROJECT_ID -r us-west1 -s juntoshq -e .env
```

After the script completes, the running Cloud Run revision is immediately updated with the new environment variables. Test at:

```
https://<your-service-url>/auth/login
```

### What the script does

1. Reads each secret value from your `.env` file.
2. Creates the secret in Secret Manager if it doesn't exist; adds a new version if it does.
3. Grants `roles/secretmanager.secretAccessor` to the Cloud Run default compute service account.
4. Calls `gcloud run services update --set-secrets=...` to inject all secrets into the live service.

> **Note:** You still need to ensure your Google OAuth client has the Cloud Run service URL listed as an **Authorized redirect URI** in the [Google Cloud Console](https://console.cloud.google.com/apis/credentials):
> ```
> https://juntoshq-93682766063.us-west1.run.app/auth/callback/google
> ```
> Without that entry, Google will block the OAuth redirect even if `client_id` is correctly configured.

### Why this happens with Cloud Build wired to the repo

`cloudbuild.yaml` uses `--set-secrets` to pull values from Secret Manager at deploy time.  If the Secret Manager secrets don't exist yet, the `gcloud run deploy` step will fail.  Run `setup-secrets.sh` once to populate Secret Manager, then every subsequent push to `main` will automatically deploy with the correct secrets.

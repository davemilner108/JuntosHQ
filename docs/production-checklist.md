# Production Launch Checklist

Step-by-step checklist for taking JuntosHQ from development to a live production deployment on Google Cloud Run.

---

## 1. Stripe Setup

- [ ] Create a Stripe account at https://stripe.com if you haven't already
- [ ] In the Stripe Dashboard, create three products with monthly recurring prices:
  - **Standard** — $4.99/month
  - **Expanded** — $9.99/month
  - **Ben's Counsel** — $4.99/month add-on
- [ ] Copy each Price ID (`price_...`) — you'll need them in Step 3
- [ ] Register the webhook endpoint in Stripe Dashboard → Developers → Webhooks:
  - Endpoint URL: `https://<your-domain>/stripe/webhook`
  - Events to enable:
    - `checkout.session.completed`
    - `customer.subscription.updated`
    - `customer.subscription.deleted`
    - `invoice.payment_failed`
- [ ] Copy the webhook signing secret (`whsec_...`)
- [ ] Switch from test mode keys to **live mode** keys before launch

---

## 2. OAuth Credentials (Production Domain)

Update both OAuth apps to allow your production domain.

### Google
1. Go to [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials
2. Open your OAuth 2.0 client
3. Add to **Authorized redirect URIs**: `https://<your-domain>/auth/callback/google`

---

## 3. Secret Manager

Store all secrets in Google Secret Manager before deploying. See [Deploying on Google Cloud](deployment-gcp.md#step-2--store-secrets-in-secret-manager) for the full `gcloud secrets create` commands.

Secrets required:

| Secret | Notes |
|---|---|
| `DATABASE_URL` | Supabase PostgreSQL URI (transaction pooler, port 6543) |
| `SECRET_KEY` | Long random string: `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `GOOGLE_CLIENT_ID` | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | From Google Cloud Console |
| `ANTHROPIC_API_KEY` | For Ben's Counsel chatbot |
| `VOYAGE_API_KEY` | For RAG embeddings |
| `STRIPE_SECRET_KEY` | Live mode key (`sk_live_...`) |
| `STRIPE_WEBHOOK_SECRET` | From Stripe webhook endpoint (`whsec_...`) |
| `STRIPE_PRICE_STANDARD` | Standard plan price ID (`price_...`) |
| `STRIPE_PRICE_EXPANDED` | Expanded plan price ID (`price_...`) |
| `STRIPE_PRICE_CHATBOT` | Ben's Counsel add-on price ID (`price_...`) |
| `MAIL_SERVER` | SMTP host (e.g. `smtp.sendgrid.net`) |
| `MAIL_USERNAME` | SMTP username |
| `MAIL_PASSWORD` | SMTP password or API key |

---

## 4. Database

- [ ] Confirm Cloud SQL / Supabase has **automated backups** enabled
- [ ] Enable the `pgvector` extension in your Supabase project:
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  ```
- [ ] Run database migrations:
  ```bash
  DB_URL=$(gcloud secrets versions access latest --secret=DATABASE_URL)
  docker run --rm \
    -e DATABASE_URL="${DB_URL}" \
    -e SECRET_KEY="placeholder-migration-only" \
    <image> .venv/bin/alembic upgrade head
  ```
- [ ] Seed the Franklin corpus for Ben's Counsel RAG:
  ```bash
  uv run python scripts/seed_franklin.py
  ```
- [ ] Run the junto tier backfill (if any juntos existed before PR #20):
  ```bash
  uv run scripts/backfill_junto_tiers.py
  ```

---

## 5. Build & Deploy

- [ ] Build and push the Docker image to Artifact Registry
- [ ] Deploy to Cloud Run with all secrets injected (see `cloudbuild.yaml` or [deployment-gcp.md](deployment-gcp.md#step-6--deploy-to-cloud-run))
- [ ] Map your custom domain and confirm TLS certificate is provisioned:
  ```bash
  gcloud run domain-mappings create \
    --service=juntoshq \
    --domain=<your-domain> \
    --region=us-west1
  ```

---

## 6. Smoke Tests

After deploying, verify each of these manually:

- [ ] Homepage loads at your domain
- [ ] Google OAuth sign-in completes and lands on homepage
- [ ] Creating a junto works for a Free user
- [ ] Junto limit is enforced (Free user can't create a second junto)
- [ ] Stripe Checkout opens for Standard plan (`/account/subscription/checkout?plan=standard`)
- [ ] Completing a test purchase upgrades the user's tier (use Stripe test card `4242 4242 4242 4242` in test mode first)
- [ ] Customer Portal opens at `/account/subscription/portal`
- [ ] Invite link is created for a Standard/Expanded user
- [ ] Invite link is blocked for a Free user with a clear upgrade message
- [ ] Ben's Counsel chatbot responds (5 free trial messages)
- [ ] `/stripe/webhook` returns 400 for unsigned requests (test with curl: `curl -X POST https://<domain>/stripe/webhook` should return 400)

---

## 7. CI/CD

Wire Cloud Build to auto-deploy on every push to `main`:

```bash
gcloud builds triggers create github \
  --repo-name=JuntosHQ \
  --repo-owner=<your-github-username> \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --region=us-west1
```

Grant Cloud Build the necessary IAM roles (see [deployment-gcp.md](deployment-gcp.md#wire-it-to-github)).

---

## 8. Monitoring & Errors

- [ ] Set up [Google Cloud Error Reporting](https://console.cloud.google.com/errors) — Cloud Run logs exceptions automatically
- [ ] Optionally add [Sentry](https://sentry.io) for richer error context:
  ```bash
  uv add sentry-sdk[flask]
  ```
  ```python
  # In create_app():
  import sentry_sdk
  sentry_sdk.init(dsn=os.environ.get("SENTRY_DSN", ""), traces_sample_rate=0.1)
  ```
- [ ] Set up an uptime monitor (e.g. [UptimeRobot](https://uptimerobot.com)) on your domain

---

## 9. Post-Launch

- [ ] Revoke any GitHub Personal Access Tokens used during setup
- [ ] Set up SSH keys or `git credential-osxkeychain` for future pushes (avoid pasting tokens in chat)
- [ ] Monitor Cloud Run logs for the first 24h: `gcloud run services logs read juntoshq --region=us-west1 --tail=50`
- [ ] Review Stripe Dashboard for any failed webhook deliveries
- [ ] Confirm invite emails are delivered (check spam folders)

---

## Related Docs

- [Configuration](configuration.md) — full environment variable reference
- [Deploying on Google Cloud](deployment-gcp.md) — detailed GCP setup
- [Database & Migrations](database.md) — Alembic workflow

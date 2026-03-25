#!/usr/bin/env bash
# setup-secrets.sh — Load .env values into GCP Secret Manager and redeploy
#                    the existing Cloud Run service with the updated secrets.
#
# Usage:
#   ./scripts/setup-secrets.sh [OPTIONS]
#
# Options:
#   -p PROJECT_ID   GCP project ID (default: current gcloud project)
#   -r REGION       Cloud Run region (default: us-west1)
#   -s SERVICE      Cloud Run service name (default: juntoshq)
#   -e ENV_FILE     Path to .env file (default: .env)
#   -h              Print this help message
#
# Examples:
#   # Basic usage — reads .env in the current directory
#   ./scripts/setup-secrets.sh
#
#   # Specify everything explicitly
#   ./scripts/setup-secrets.sh -p my-gcp-project -r us-west1 -s juntoshq -e .env
#
# The script creates or updates each Secret Manager secret, then runs
#   gcloud run services update
# to inject them into the live Cloud Run service without requiring a full rebuild.

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
REGION="us-west1"
SERVICE="juntoshq"
ENV_FILE=".env"
PROJECT_ID=""

# ── Secrets that are injected into Cloud Run ──────────────────────────────────
# Each name here must correspond to a key in the .env file and will become a
# Secret Manager secret of the same name.
REQUIRED_SECRETS=(
  DATABASE_URL
  SECRET_KEY
  GOOGLE_CLIENT_ID
  GOOGLE_CLIENT_SECRET
  GITHUB_CLIENT_ID
  GITHUB_CLIENT_SECRET
  ANTHROPIC_API_KEY
  VOYAGE_API_KEY
)

OPTIONAL_SECRETS=(
  STRIPE_SECRET_KEY
  STRIPE_WEBHOOK_SECRET
  STRIPE_PRICE_STANDARD
  STRIPE_PRICE_EXPANDED
  STRIPE_PRICE_CHATBOT
  MAIL_SERVER
  MAIL_PORT
  MAIL_USERNAME
  MAIL_PASSWORD
  MAIL_DEFAULT_SENDER
  OPENAI_API_KEY
)

# ── Parse arguments ────────────────────────────────────────────────────────────
while getopts "p:r:s:e:h" opt; do
  case "$opt" in
    p) PROJECT_ID="$OPTARG" ;;
    r) REGION="$OPTARG" ;;
    s) SERVICE="$OPTARG" ;;
    e) ENV_FILE="$OPTARG" ;;
    h)
      sed -n '/^# /p' "$0" | sed 's/^# //'
      exit 0
      ;;
    *) echo "Unknown option: $opt" >&2; exit 1 ;;
  esac
done

# ── Resolve project ID ─────────────────────────────────────────────────────────
if [[ -z "$PROJECT_ID" ]]; then
  PROJECT_ID=$(gcloud config get-value project 2>/dev/null || true)
fi
if [[ -z "$PROJECT_ID" ]]; then
  echo "ERROR: Cannot determine GCP project ID." >&2
  echo "       Either run  gcloud config set project YOUR_PROJECT_ID" >&2
  echo "       or pass     -p YOUR_PROJECT_ID" >&2
  exit 1
fi

echo "Project : $PROJECT_ID"
echo "Region  : $REGION"
echo "Service : $SERVICE"
echo "Env file: $ENV_FILE"
echo ""

# ── Check .env file exists ─────────────────────────────────────────────────────
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found. Create it from .env.example and fill in your values." >&2
  exit 1
fi

# ── Helper: read a value from the .env file ────────────────────────────────────
get_env_value() {
  local key="$1"
  # Strip inline comments, surrounding quotes, and leading/trailing whitespace.
  grep -E "^${key}=" "$ENV_FILE" 2>/dev/null \
    | tail -1 \
    | sed "s/^${key}=//" \
    | sed 's/[[:space:]]*#.*//' \
    | sed "s/^['\"]//;s/['\"]$//" \
    | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' \
    || true
}

# ── Helper: create or update a Secret Manager secret ──────────────────────────
upsert_secret() {
  local name="$1"
  local value="$2"

  if gcloud secrets describe "$name" --project="$PROJECT_ID" &>/dev/null; then
    echo "  Updating secret: $name"
    printf '%s' "$value" | \
      gcloud secrets versions add "$name" \
        --project="$PROJECT_ID" \
        --data-file=-
  else
    echo "  Creating secret: $name"
    printf '%s' "$value" | \
      gcloud secrets create "$name" \
        --project="$PROJECT_ID" \
        --replication-policy="automatic" \
        --data-file=-
  fi
}

# ── Push secrets to Secret Manager ────────────────────────────────────────────
echo "=== Pushing secrets to Secret Manager ==="

SET_SECRETS_ARG=""
MISSING_REQUIRED=()

for key in "${REQUIRED_SECRETS[@]}"; do
  value=$(get_env_value "$key")
  if [[ -z "$value" ]]; then
    MISSING_REQUIRED+=("$key")
    continue
  fi
  upsert_secret "$key" "$value"
  SET_SECRETS_ARG="${SET_SECRETS_ARG}${key}=${key}:latest,"
done

for key in "${OPTIONAL_SECRETS[@]}"; do
  value=$(get_env_value "$key")
  if [[ -z "$value" ]]; then
    continue
  fi
  upsert_secret "$key" "$value"
  SET_SECRETS_ARG="${SET_SECRETS_ARG}${key}=${key}:latest,"
done

# Strip trailing comma
SET_SECRETS_ARG="${SET_SECRETS_ARG%,}"

if [[ ${#MISSING_REQUIRED[@]} -gt 0 ]]; then
  echo ""
  echo "WARNING: The following required secrets were missing from $ENV_FILE and were skipped:"
  for key in "${MISSING_REQUIRED[@]}"; do
    echo "  - $key"
  done
  echo ""
  echo "Add them to $ENV_FILE and re-run this script, or set them manually:"
  echo "  echo -n 'VALUE' | gcloud secrets create KEY --data-file=- --project=$PROJECT_ID"
  echo ""
fi

# ── Grant Cloud Run service account access to secrets ─────────────────────────
echo ""
echo "=== Granting Cloud Run service account access to secrets ==="
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
CR_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${CR_SA}" \
  --role="roles/secretmanager.secretAccessor" \
  --quiet

echo "  Granted roles/secretmanager.secretAccessor to $CR_SA"

# ── Update the Cloud Run service with the new secrets ─────────────────────────
echo ""
echo "=== Updating Cloud Run service '$SERVICE' in $REGION ==="

if [[ -z "$SET_SECRETS_ARG" ]]; then
  echo "ERROR: No secrets to inject — nothing to update." >&2
  exit 1
fi

gcloud run services update "$SERVICE" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --update-secrets="$SET_SECRETS_ARG"

echo ""
echo "=== Done! ==="
echo ""
echo "The Cloud Run service has been updated with the latest secret values."
echo "Test the OAuth login at:"
SERVICE_URL=$(gcloud run services describe "$SERVICE" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --format="value(status.url)" 2>/dev/null || true)
if [[ -n "$SERVICE_URL" ]]; then
  echo "  ${SERVICE_URL}/auth/login"
else
  echo "  https://<your-service-url>/auth/login"
fi

#!/bin/bash
set -e

PROJECT_ID=${GCP_PROJECT_ID:?GCP_PROJECT_ID not set}
REGION="europe-west1"
SA_NAME="news-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=== Setting up News Intelligence Pipeline ==="
echo "Project: $PROJECT_ID | Region: $REGION"

# APIs
gcloud services enable \
  run.googleapis.com \
  cloudscheduler.googleapis.com \
  bigquery.googleapis.com \
  aiplatform.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  --project=$PROJECT_ID

# Service Account
gcloud iam service-accounts create $SA_NAME \
  --display-name="News Intelligence SA" \
  --project=$PROJECT_ID 2>/dev/null || echo "SA already exists"

# IAM roles
for ROLE in \
  roles/bigquery.dataEditor \
  roles/bigquery.jobUser \
  roles/aiplatform.user \
  roles/secretmanager.secretAccessor; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="$ROLE" --quiet
done

# Secrets
echo "Creating secrets (you'll need to set values)..."
for SECRET in TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID; do
  gcloud secrets create $SECRET --project=$PROJECT_ID 2>/dev/null || true
  echo "  → Set value: gcloud secrets versions add $SECRET --data-file=-"
done

# BigQuery tables
export PROJECT=$PROJECT_ID
envsubst < infra/bq_init.sql | bq query --use_legacy_sql=false

echo ""
echo "=== Setup complete ==="
echo "Next: set secret values, then run: bash infra/deploy.sh"

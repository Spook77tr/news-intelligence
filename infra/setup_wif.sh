#!/bin/bash
# One-time setup: Workload Identity Federation + Artifact Registry
# Run this once before the first CI/CD push.
#
# Usage:
#   export GCP_PROJECT_ID=your-project-id
#   export GITHUB_REPO=your-org/news-intelligence   # e.g. acme/news-intelligence
#   bash infra/setup_wif.sh
set -e

PROJECT_ID=${GCP_PROJECT_ID:?GCP_PROJECT_ID not set}
GITHUB_REPO=${GITHUB_REPO:?GITHUB_REPO not set (format: owner/repo)}
REGION="europe-west1"
SA_EMAIL="news-sa@${PROJECT_ID}.iam.gserviceaccount.com"
POOL_ID="github-pool"
PROVIDER_ID="github-provider"

echo "=== WIF + Artifact Registry Setup ==="
echo "Project : $PROJECT_ID"
echo "Repo    : $GITHUB_REPO"
echo ""

# Enable required APIs
gcloud services enable \
  artifactregistry.googleapis.com \
  iamcredentials.googleapis.com \
  --project=$PROJECT_ID

# --- Artifact Registry ---
echo "--- Artifact Registry ---"
gcloud artifacts repositories create news-intelligence \
  --repository-format=docker \
  --location=$REGION \
  --description="News Intelligence Pipeline images" \
  --project=$PROJECT_ID 2>/dev/null || echo "Repository already exists"

# Grant SA push access to Artifact Registry
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/artifactregistry.writer" \
  --quiet

# --- Workload Identity Pool ---
echo ""
echo "--- Workload Identity Pool ---"
gcloud iam workload-identity-pools create $POOL_ID \
  --location=global \
  --display-name="GitHub Actions Pool" \
  --project=$PROJECT_ID 2>/dev/null || echo "Pool already exists"

POOL_NAME=$(gcloud iam workload-identity-pools describe $POOL_ID \
  --location=global \
  --project=$PROJECT_ID \
  --format="value(name)")

# --- Workload Identity Provider ---
echo ""
echo "--- Workload Identity Provider ---"
gcloud iam workload-identity-pools providers create-oidc $PROVIDER_ID \
  --location=global \
  --workload-identity-pool=$POOL_ID \
  --display-name="GitHub Actions Provider" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.actor=assertion.actor,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository=='${GITHUB_REPO}'" \
  --project=$PROJECT_ID 2>/dev/null || echo "Provider already exists"

PROVIDER_NAME=$(gcloud iam workload-identity-pools providers describe $PROVIDER_ID \
  --location=global \
  --workload-identity-pool=$POOL_ID \
  --project=$PROJECT_ID \
  --format="value(name)")

# --- Bind WIF to Service Account ---
echo ""
echo "--- Binding WIF to Service Account ---"
gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${POOL_NAME}/attribute.repository/${GITHUB_REPO}" \
  --project=$PROJECT_ID

# Grant SA permission to deploy Cloud Run Jobs
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.developer" \
  --quiet

# Allow SA to act as itself when submitting jobs (needed for --service-account flag)
gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
  --role="roles/iam.serviceAccountUser" \
  --member="serviceAccount:${SA_EMAIL}" \
  --project=$PROJECT_ID

echo ""
echo "=== Done! Add these secrets to GitHub (Settings → Secrets → Actions) ==="
echo ""
echo "  GCP_PROJECT_ID   = ${PROJECT_ID}"
echo "  GCP_WIF_PROVIDER = ${PROVIDER_NAME}"
echo "  GCP_SA_EMAIL     = ${SA_EMAIL}"
echo ""
echo "Quick add via gh CLI:"
echo "  gh secret set GCP_PROJECT_ID   --body '${PROJECT_ID}'"
echo "  gh secret set GCP_WIF_PROVIDER --body '${PROVIDER_NAME}'"
echo "  gh secret set GCP_SA_EMAIL     --body '${SA_EMAIL}'"

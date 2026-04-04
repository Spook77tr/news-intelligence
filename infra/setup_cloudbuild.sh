#!/bin/bash
# One-time setup: Cloud Build permissions + trigger.
#
# Prerequisites (must be done in GCP Console FIRST):
#   Console → Cloud Build → Repositories (2nd gen)
#   → Connect Repository → GitHub → Authorize → select Spook77tr/news-intelligence
#
# Usage:
#   export GCP_PROJECT_ID=bi4ward
#   bash infra/setup_cloudbuild.sh
set -e

PROJECT_ID=${GCP_PROJECT_ID:?GCP_PROJECT_ID not set}
REGION="europe-west1"
SA_EMAIL="news-sa@${PROJECT_ID}.iam.gserviceaccount.com"
GITHUB_OWNER="Spook77tr"
GITHUB_REPO="news-intelligence"
TRIGGER_NAME="news-intelligence-deploy"

echo "=== Cloud Build Setup ==="
echo "Project : $PROJECT_ID"
echo ""

# Enable APIs
gcloud services enable \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  --project=$PROJECT_ID

# Get Cloud Build service account
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
CLOUDBUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
echo "Cloud Build SA: $CLOUDBUILD_SA"

# Grant Cloud Build SA the roles it needs
echo ""
echo "--- Granting IAM roles to Cloud Build SA ---"
for ROLE in \
  roles/run.developer \
  roles/iam.serviceAccountUser \
  roles/artifactregistry.writer \
  roles/secretmanager.secretAccessor \
  roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUDBUILD_SA}" \
    --role="$ROLE" \
    --condition=None \
    --quiet
  echo "  ✓ $ROLE"
done

# Artifact Registry repo (idempotent)
echo ""
echo "--- Artifact Registry ---"
gcloud artifacts repositories create news-intelligence \
  --repository-format=docker \
  --location=$REGION \
  --description="News Intelligence Pipeline images" \
  --project=$PROJECT_ID 2>/dev/null || echo "  Repository already exists"

# Create Cloud Build trigger (2nd gen — requires repo connection to exist)
echo ""
echo "--- Creating Cloud Build trigger ---"
gcloud builds triggers create github \
  --name="$TRIGGER_NAME" \
  --repo-owner="$GITHUB_OWNER" \
  --repo-name="$GITHUB_REPO" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml" \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --description="Push to main → build + deploy all jobs" \
  2>/dev/null || \
gcloud builds triggers update "$TRIGGER_NAME" \
  --build-config="cloudbuild.yaml" \
  --region="$REGION" \
  --project="$PROJECT_ID"

echo ""
echo "=== Done! ==="
echo ""
echo "Trigger created: $TRIGGER_NAME"
echo "View in Console:"
echo "  https://console.cloud.google.com/cloud-build/triggers?project=$PROJECT_ID"
echo ""
echo "Manually run a build:"
echo "  gcloud builds triggers run $TRIGGER_NAME --branch=main --region=$REGION --project=$PROJECT_ID"

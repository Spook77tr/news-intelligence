#!/bin/bash
set -e

PROJECT_ID=${GCP_PROJECT_ID:?GCP_PROJECT_ID not set}
REGION="europe-west1"
SA_EMAIL="news-sa@${PROJECT_ID}.iam.gserviceaccount.com"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/news-intelligence"

JOBS=(fetcher processor notifier)
TARGET=${1:-all}  # bash infra/deploy.sh fetcher → sadece fetcher

deploy_job() {
  JOB=$1
  IMAGE="${REGISTRY}/news-${JOB}:latest"

  echo "=== Building ${JOB} ==="
  gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet
  docker build \
    -f jobs/${JOB}/Dockerfile \
    -t $IMAGE \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    .

  docker push $IMAGE

  echo "=== Deploying Cloud Run Job: news-${JOB} ==="
  gcloud run jobs update news-${JOB} \
    --image=$IMAGE \
    --region=$REGION \
    --service-account=$SA_EMAIL \
    --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},BQ_DATASET=news_intelligence" \
    --set-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest,TELEGRAM_BOT_TOKEN=TELEGRAM_BOT_TOKEN:latest,TELEGRAM_CHAT_ID=TELEGRAM_CHAT_ID:latest" \
    --memory=2Gi \
    --task-timeout=1800 \
    --project=$PROJECT_ID 2>/dev/null || \
  gcloud run jobs create news-${JOB} \
    --image=$IMAGE \
    --region=$REGION \
    --service-account=$SA_EMAIL \
    --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},BQ_DATASET=news_intelligence" \
    --set-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest,TELEGRAM_BOT_TOKEN=TELEGRAM_BOT_TOKEN:latest,TELEGRAM_CHAT_ID=TELEGRAM_CHAT_ID:latest" \
    --memory=2Gi \
    --task-timeout=1800 \
    --project=$PROJECT_ID

  echo "✓ ${JOB} deployed"
}

if [ "$TARGET" = "all" ]; then
  for JOB in "${JOBS[@]}"; do deploy_job $JOB; done
else
  deploy_job $TARGET
fi

# Schedulers (only on full deploy)
if [ "$TARGET" = "all" ]; then
  echo "=== Setting up Cloud Schedulers ==="

  BASE_URL="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs"

  for JOB_SCHED in "fetcher:30 5 * * *" "processor:45 5 * * *" "notifier:15 6 * * *"; do
    JOB="${JOB_SCHED%%:*}"
    SCHEDULE="${JOB_SCHED##*:}"
    NAME="news-${JOB}-trigger"

    gcloud scheduler jobs delete $NAME --location=$REGION --quiet 2>/dev/null || true
    gcloud scheduler jobs create http $NAME \
      --location=$REGION \
      --schedule="$SCHEDULE" \
      --time-zone="Europe/Istanbul" \
      --uri="${BASE_URL}/news-${JOB}:run" \
      --http-method=POST \
      --oauth-service-account-email=$SA_EMAIL \
      --project=$PROJECT_ID
    echo "✓ Scheduler: $NAME ($SCHEDULE TR)"
  done
fi

echo ""
echo "=== Deploy complete ==="

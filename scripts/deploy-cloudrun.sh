#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null | tr -d '\r')}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-hw-kai-backend}"
MODEL_NAME="${MODEL_NAME:-gpt-4o-mini}"
IMAGE_NAME="${IMAGE_NAME:-gcr.io/${PROJECT_ID}/hw-kai-backend}"
SECRET_NAME="openai-api-key"

if [[ -z "$PROJECT_ID" || "$PROJECT_ID" == "(unset)" ]]; then
  echo "❌ PROJECT_ID 未设置，请先运行: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

for api in run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com; do
  gcloud services enable "$api" --project="$PROJECT_ID" >/dev/null
done

if ! gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "❌ 缺少 secret: $SECRET_NAME"
  echo "先运行: OPENAI_API_KEY=YOUR_KEY ./scripts/set-openai-secret.sh"
  exit 1
fi

TEMP_DOCKERFILE_CREATED=0
if [[ ! -f Dockerfile ]]; then
  cp Dockerfile.backend Dockerfile
  TEMP_DOCKERFILE_CREATED=1
fi
cleanup() {
  if [[ "$TEMP_DOCKERFILE_CREATED" == "1" ]]; then rm -f Dockerfile; fi
}
trap cleanup EXIT

echo "== Building image =="
gcloud builds submit --project="$PROJECT_ID" --tag "$IMAGE_NAME" .

echo "== Grant Secret access to Cloud Run service account =="
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project="$PROJECT_ID" >/dev/null || true

echo "== Deploying Cloud Run =="
gcloud run deploy "$SERVICE_NAME" \
  --project="$PROJECT_ID" \
  --image "$IMAGE_NAME" \
  --platform managed \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "DATA_DIR=/app/data,OPENAI_BASE_URL=https://api.openai.com/v1,MODEL_NAME=${MODEL_NAME}" \
  --set-secrets "OPENAI_API_KEY=${SECRET_NAME}:latest"

echo
SERVICE_URL="$(gcloud run services describe "$SERVICE_NAME" --project="$PROJECT_ID" --region="$REGION" --format='value(status.url)')"
echo "✅ Deploy 完成: $SERVICE_URL"

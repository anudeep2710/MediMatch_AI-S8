#!/usr/bin/env bash
set -euo pipefail

# Config
PROJECT_ID="${PROJECT_ID:-crafty-plateau-490307-s2}"
SERVICE_NAME="${SERVICE_NAME:-medimatch}"
REGION="${REGION:-us-central1}"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "Building and pushing image to ${IMAGE}..."
gcloud config set project "${PROJECT_ID}"
gcloud builds submit --tag "${IMAGE}"

echo "Deploying to Cloud Run service ${SERVICE_NAME} in ${REGION}..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --port 8080 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --set-env-vars FLASK_RELOAD=false \
  --set-env-vars DATABASE_URL="${DATABASE_URL:-}" \
  --set-env-vars GROQ_API_KEY="${GROQ_API_KEY:-}" \
  --set-env-vars SERPER_API_KEY="${SERPER_API_KEY:-}" \
  --set-env-vars GEMINI_API_KEY="${GEMINI_API_KEY:-}" \
  --set-env-vars KG_FAISS_INDEX="${KG_FAISS_INDEX:-}" \
  --set-env-vars KG_FAISS_META="${KG_FAISS_META:-}" \
  --set-env-vars KG_FAISS_SRC="${KG_FAISS_SRC:-}" \
  --set-env-vars KG_FAISS_META_SRC="${KG_FAISS_META_SRC:-}"

echo "Done. Service URL:"
gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --format='value(status.url)'

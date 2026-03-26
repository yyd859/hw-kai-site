#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null | tr -d '\r')}"
SECRET_NAME="openai-api-key"
KEY="${OPENAI_API_KEY:-}"

if [[ -z "$PROJECT_ID" || "$PROJECT_ID" == "(unset)" ]]; then
  echo "❌ PROJECT_ID 未设置，请先运行: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

if [[ -z "$KEY" ]]; then
  read -r -s -p "OpenAI API Key: " KEY
  echo
fi

if [[ -z "$KEY" ]]; then
  echo "❌ 没有提供 OpenAI API Key"
  exit 1
fi

if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo -n "$KEY" | gcloud secrets versions add "$SECRET_NAME" --data-file=- --project="$PROJECT_ID" >/dev/null
  echo "✅ 已更新 secret: $SECRET_NAME"
else
  echo -n "$KEY" | gcloud secrets create "$SECRET_NAME" --data-file=- --project="$PROJECT_ID" >/dev/null
  echo "✅ 已创建 secret: $SECRET_NAME"
fi

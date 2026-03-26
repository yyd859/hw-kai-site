#!/usr/bin/env bash
set -euo pipefail

echo "== hw-kai backend preflight =="
command -v gcloud >/dev/null 2>&1 && echo "✅ gcloud 已安装" || { echo "❌ 未安装 gcloud"; exit 1; }
command -v docker >/dev/null 2>&1 && echo "✅ docker 已安装" || echo "⚠️ 未安装 docker（可选，Cloud Build 可不用本地 docker）"

echo "== gcloud auth =="
gcloud auth list --filter=status:ACTIVE || true

echo "== current project =="
gcloud config get-value project || true

echo "== required apis =="
for api in run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com; do
  if gcloud services list --enabled --format='value(config.name)' | grep -qx "$api"; then
    echo "✅ $api"
  else
    echo "⚠️ $api 未启用"
  fi
done

echo
printf 'Next:\n  1) gcloud auth login\n  2) gcloud config set project YOUR_PROJECT_ID\n  3) ./scripts/set-openai-secret.sh\n  4) ./scripts/deploy-cloudrun.sh\n'

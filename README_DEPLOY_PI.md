# HW-KAI Backend 部署到 Google Cloud Run（树莓派 / Mac / Linux）

## 先决条件

### 1. 安装 gcloud
Debian / Ubuntu / Raspberry Pi OS:
```bash
curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt update
sudo apt install -y google-cloud-cli
```

### 2. 登录并设置 project
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 3. 预检查
```bash
chmod +x scripts/*.sh
./scripts/cloudrun-preflight.sh
```

## 设置 OpenAI secret
```bash
OPENAI_API_KEY="YOUR_OPENAI_KEY" ./scripts/set-openai-secret.sh
```

## 部署
```bash
./scripts/deploy-cloudrun.sh
```

可选：
```bash
PROJECT_ID="YOUR_PROJECT_ID" REGION="us-central1" ./scripts/deploy-cloudrun.sh
```

## 测试
```bash
curl https://YOUR_CLOUD_RUN_URL/health
```

## 说明
- Dockerfile 使用项目根目录 build context
- Cloud Run 会读取 `/app/data`
- secret 名默认是 `openai-api-key`
- 前端可通过 `?apiBase=https://xxx.run.app` 指向后端

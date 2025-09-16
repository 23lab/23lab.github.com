#!/usr/bin/env bash
set -euo pipefail

# Build and deploy the Dockerized site to an Alibaba Cloud ECS instance via SSH.
# Requirements:
# - Docker installed locally
# - SSH access to ECS with sudo docker permissions
# - ENV VARS: ECS_HOST, ECS_USER, SSH_KEY, APP_NAME (default: we-bank-site-demo)

APP_NAME=${APP_NAME:-we-bank-site-demo}
ECS_HOST=${ECS_HOST:-}
ECS_USER=${ECS_USER:-root}
SSH_KEY=${SSH_KEY:-"$HOME/.ssh/id_rsa"}
REMOTE_PORT=${REMOTE_PORT:-80}

if [[ -z "$ECS_HOST" ]]; then
  echo "Please export ECS_HOST, e.g.: export ECS_HOST=xx.xx.xx.xx" >&2
  exit 2
fi

echo "Building Docker image..."
docker build -t ${APP_NAME}:latest .

echo "Saving image as tar..."
TMP_TAR=$(mktemp /tmp/${APP_NAME}.XXXXXX.tar)
docker save ${APP_NAME}:latest -o "$TMP_TAR"

echo "Copying image to ECS..."
scp -i "$SSH_KEY" -o StrictHostKeyChecking=no "$TMP_TAR" ${ECS_USER}@${ECS_HOST}:/tmp/${APP_NAME}.tar
rm -f "$TMP_TAR"

echo "Loading and running container on ECS..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no ${ECS_USER}@${ECS_HOST} "\
  docker load -i /tmp/${APP_NAME}.tar && \
  docker rm -f ${APP_NAME} 2>/dev/null || true && \
  docker run -d --name ${APP_NAME} --restart unless-stopped -p ${REMOTE_PORT}:80 ${APP_NAME}:latest && \
  rm -f /tmp/${APP_NAME}.tar && \
  docker images prune -f && docker container prune -f
"

echo "Deployment completed. Visit: http://${ECS_HOST}:${REMOTE_PORT}"


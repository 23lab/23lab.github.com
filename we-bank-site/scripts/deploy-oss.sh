#!/usr/bin/env bash
set -euo pipefail

# Deploy static site to Alibaba Cloud OSS
# Requirements:
# - aliyun CLI installed and configured: `aliyun configure`
# - OSS bucket exists with public read or behind CDN
# - ENV VARS: OSS_BUCKET, OSS_REGION (e.g. cn-hangzhou), OPTIONAL: OSS_PREFIX

if ! command -v aliyun >/dev/null 2>&1; then
  echo "aliyun CLI not found. Install: https://help.aliyun.com/zh/cli/" >&2
  exit 1
fi

OSS_BUCKET=${OSS_BUCKET:-}
OSS_REGION=${OSS_REGION:-}
OSS_PREFIX=${OSS_PREFIX:-}
SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)/public"

if [[ -z "$OSS_BUCKET" || -z "$OSS_REGION" ]]; then
  echo "Please export OSS_BUCKET and OSS_REGION, e.g.:" >&2
  echo "  export OSS_BUCKET=your-bucket-name" >&2
  echo "  export OSS_REGION=cn-hangzhou" >&2
  exit 2
fi

echo "Uploading $SRC_DIR to oss://$OSS_BUCKET/${OSS_PREFIX}" 

# Ensure bucket exists
aliyun oss HeadBucket --bucket-name "$OSS_BUCKET" --region "$OSS_REGION" >/dev/null 2>&1 || {
  echo "Bucket $OSS_BUCKET not found in $OSS_REGION" >&2
  exit 3
}

# Sync files
aliyun oss cp "${SRC_DIR}" "oss://${OSS_BUCKET}/${OSS_PREFIX}" --recursive --region "$OSS_REGION" --force

echo "Setting cache headers for static assets..."
aliyun oss set-object-meta --region "$OSS_REGION" \
  --bucket-name "$OSS_BUCKET" \
  --object-name "${OSS_PREFIX%/}/assets/" \
  --headers '{"Cache-Control":"public, max-age=2592000"}' || true

echo "Done. Consider binding CDN to OSS for best performance."


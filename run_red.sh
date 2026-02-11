#!/usr/bin/env bash
set -euo pipefail

IMAGE="red-red"
NAME="red"
PORT="127.0.0.1:8111:8111"
NET="rednet"
VOL="red_memory"

docker volume create "$VOL" >/dev/null 2>&1 || true

docker rm -f "$NAME" >/dev/null 2>&1 || true

docker run -d \
  --name "$NAME" \
  --network "$NET" \
  -p "$PORT" \
  -v "$VOL":/red/data \
  -e MEMORY_STORE_PATH="/red/data/memory.json" \
  -e AUDIT_LOG_PATH="/red/data/memory_audit.jsonl" \
  -e CONTROL_PLANE_URL="http://meeks-control-plane:8088" \
  -e ENABLE_SHADOW_OBSERVER=true \
  -e ENABLE_BU3_INGEST=true \
  -e APPROVAL_SIGNING_SECRET="shadowobserverdevsecret123" \
  "$IMAGE"

echo "Red started."
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}" | grep -E "^red[[:space:]]"

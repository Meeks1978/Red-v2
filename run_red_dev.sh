#!/usr/bin/env bash
set -euo pipefail

IMAGE="red-red"
NAME="red"
NET="rednet"
VOL="red_memory"
PORT="127.0.0.1:8111:8111"

docker volume create "$VOL" >/dev/null 2>&1 || true
docker rm -f "$NAME" >/dev/null 2>&1 || true

docker run -d \
  --name "$NAME" \
  --network "$NET" \
  -p "$PORT" \
  -v "$VOL":/red/data \
  -e INVARIANTS_STRICT=false \
  -e MEMORY_STORE_PATH="/red/data/memory.json" \
  -e AUDIT_LOG_PATH="/red/data/memory_audit.jsonl" \
  -e CONTROL_PLANE_URL="http://meeks-control-plane:8088" \
  -e ENABLE_SHADOW_OBSERVER=true \
  -e ENABLE_BU3_INGEST=true \
  -e ENABLE_SEMANTIC_MEMORY=true \
  -e QDRANT_URL="http://qdrant:6333" \
  -e QDRANT_COLLECTION="red_memory_semantic" \
  -e QDRANT_DIM="384" \
  -e SEMANTIC_BUDGET_MS="50" \
  -e SEMANTIC_CB_FAILS="5" \
  -e SEMANTIC_CB_WINDOW_SEC="60" \
  -e SEMANTIC_CB_COOLDOWN_SEC="300" \
  -e APPROVAL_SIGNING_SECRET="shadowobserverdevsecret123" \
  "$IMAGE"

echo "Red started (DEV)."

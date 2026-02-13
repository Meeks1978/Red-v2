#!/usr/bin/env bash
set -euo pipefail

# Ensure network exists
docker network create rednet 2>/dev/null || true

# Ensure dependencies are on the same network (idempotent)
docker network connect rednet meeks-control-plane 2>/dev/null || true
docker network connect rednet qdrant 2>/dev/null || true

# Remove old container (if any)
docker rm -f red 2>/dev/null || true

# Ensure data volume exists
docker volume create red_memory >/dev/null 2>&1 || true

docker run -d \
  --name red \
  --network rednet \
  -p 127.0.0.1:8111:8111 \
  -v red_memory:/red/data \
  -e CONTROL_PLANE_URL="http://meeks-control-plane:8088" \
  -e ENABLE_SHADOW_OBSERVER=true \
  -e EXECUTOR_ENABLED=true \
  -e RED_DEV_MODE="${RED_DEV_MODE:-false}" \
  -e RED_DEV_KEY="${RED_DEV_KEY:-}" \
  -e ENABLE_BU3_INGEST=true \
  -e ENABLE_SEMANTIC_MEMORY=true \
  -e QDRANT_URL="http://qdrant:6333" \
  -e QDRANT_COLLECTION="red_memory_semantic" \
  -e QDRANT_DIM="384" \
  -e APPROVAL_SIGNING_SECRET="${APPROVAL_SIGNING_SECRET:-shadowobserverdevsecret123}" \
  red-red

sleep 1
curl -fsS http://127.0.0.1:8111/health >/dev/null
echo "[red-up] OK"

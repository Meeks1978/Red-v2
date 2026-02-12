#!/usr/bin/env bash
set -euo pipefail

docker rm -f red 2>/dev/null || true
docker volume create red_memory >/dev/null 2>&1 || true

docker run -d \
  --name red \
  --network rednet \
  -p 127.0.0.1:8111:8111 \
  -v red_memory:/red/data \
  -e CONTROL_PLANE_URL="http://meeks-control-plane:8088" \
  -e ENABLE_SHADOW_OBSERVER=true \
  -e ENABLE_BU3_INGEST=true \
  -e ENABLE_SEMANTIC_MEMORY=true \
  -e QDRANT_URL="http://qdrant:6333" \
  -e QDRANT_COLLECTION="red_memory_semantic" \
  -e QDRANT_DIM="384" \
  red-red

sleep 1
curl -fsS http://127.0.0.1:8111/health >/dev/null
echo "[red-up] OK"

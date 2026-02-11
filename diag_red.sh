#!/usr/bin/env bash
set -euo pipefail

echo "== docker ps red =="
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" | grep -E "^red[[:space:]]" || true
echo

echo "== docker logs red (last 120) =="
docker logs red --tail 120 2>/dev/null || true
echo

echo "== data volume listing (if container runs) =="
docker exec red sh -lc 'ls -lah /red/data || true' 2>/dev/null || true

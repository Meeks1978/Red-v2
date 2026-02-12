#!/usr/bin/env bash
set -euo pipefail
BASE="${RED_BASE:-http://127.0.0.1:8111}"

echo "[BU4] health"
curl -sS "$BASE/health" ; echo

echo "[BU4] snapshot"
curl -sS "$BASE/v1/world/snapshot" ; echo

echo "[BU4] drift baseline"
D0="$(curl -sS "$BASE/v1/world/drift?limit=10")"
echo "$D0" ; echo

echo "[BU4] entity upsert"
TS="$(date +%s)"
curl -sS -X POST "$BASE/v1/world/entities" \
  -H "Content-Type: application/json" \
  -d "{\"entity_id\":\"bu4_smoke_$TS\",\"kind\":\"service\",\"attrs\":{\"k\":\"v1\"}}" ; echo

echo "[BU4] drift after"
curl -sS "$BASE/v1/world/drift?limit=10" ; echo

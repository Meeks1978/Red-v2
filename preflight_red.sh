#!/usr/bin/env bash
set -euo pipefail

BASE="http://localhost:8111"

echo "== health =="
curl -s "$BASE/health"; echo; echo

echo "== memory stats =="
curl -s "$BASE/v1/memory/stats"; echo; echo

echo "== observer metrics =="
curl -s "$BASE/observer/metrics" || true; echo; echo

echo "== audit tail =="
curl -s "$BASE/v1/memory/audit?limit=5" || true; echo; echo

echo "== done =="

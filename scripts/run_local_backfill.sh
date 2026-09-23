#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCK="$ROOT/.local/backfill.lock"
LOG_DIR="$ROOT/.local/logs"
mkdir -p "$ROOT/.local" "$LOG_DIR"
if ! mkdir "$LOCK" 2>/dev/null; then
  echo "Another local backfill is already running"
  exit 0
fi
trap 'rmdir "$LOCK"' EXIT
cd "$ROOT"

# Pick up the 09:00 cloud news refresh before adding locally authenticated cases.
git pull --ff-only origin main

set +e
python3 scripts/collect_social_chrome.py
collector_status=$?
set -e
if [[ $collector_status -eq 2 ]]; then
  echo "No platform produced a safe snapshot; keeping all last-good cases"
  exit 0
fi
if [[ $collector_status -ne 0 ]]; then
  exit "$collector_status"
fi

python3 scripts/refresh_pipeline.py
python3 scripts/cache_covers.py
python3 scripts/validate_news.py
python3 scripts/validate_topcase.py

if git diff --quiet -- dist/data data/staging data/last_good dist/assets/covers; then
  echo "No local backfill changes to publish"
  exit 0
fi
git add dist/data data/staging data/last_good dist/assets/covers
git commit -m "Backfill authenticated social cases"
if ! git push origin main; then
  git pull --rebase origin main
  git push origin main
fi

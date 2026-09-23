#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

python3 scripts/collect_news.py
python3 scripts/refresh_events.py
python3 scripts/validate_news.py

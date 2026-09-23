#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.car-radar.backfill"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"
mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/.local/logs"
python3 - "$ROOT/deploy/com.car-radar.backfill.plist.template" "$TARGET" "$ROOT" <<'PY'
from pathlib import Path
import sys
source, target, root = map(Path, sys.argv[1:])
target.write_text(source.read_text(encoding="utf-8").replace("__PROJECT_DIR__", str(root)), encoding="utf-8")
PY
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$TARGET"
launchctl enable "gui/$(id -u)/$LABEL"
echo "Installed $TARGET"
echo "The job runs at 09:15, at login, or after wake if the scheduled time was missed."

#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
echo "车势 Radar 将复用你当前 Google Chrome 的登录状态。"
echo "请在 Chrome 菜单中打开：显示 → 开发者 → 允许 Apple 事件中的 JavaScript。"
echo "然后运行：python3 scripts/collect_social_chrome.py"

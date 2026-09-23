#!/usr/bin/env python3
"""Audit Top Case coverage without changing dashboard data."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "dist" / "data" / "hotspots.json"
DEFAULT_CONFIG = ROOT / "config" / "topcase-collection.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--strict", action="store_true", help="fail when a quota or cover requirement is unmet")
    args = parser.parse_args()

    data = json.loads(args.data.read_text(encoding="utf-8"))
    config = json.loads(args.config.read_text(encoding="utf-8"))
    cases = [item for item in data.get("items", []) if item.get("type") == "case"]
    counts = Counter(item.get("platform") for item in cases)
    quota = config["dailyQuotaPerPlatform"]
    missing_covers = [item.get("id", "<missing-id>") for item in cases if not item.get("cover")]
    missing_fields = {
        item.get("id", "<missing-id>"): [field for field in config["requiredFields"] if not item.get(field)]
        for item in cases
    }
    missing_fields = {key: fields for key, fields in missing_fields.items() if fields}

    print(f"Top Case total: {len(cases)} / {quota * len(config['platforms'])}")
    for platform in config["platforms"]:
        print(f"- {platform}: {counts[platform]} / {quota}")
    print(f"Cases without cover: {len(missing_covers)}")
    if missing_fields:
        print(f"Cases with missing required fields: {len(missing_fields)}")

    incomplete = any(counts[platform] < quota for platform in config["platforms"])
    incomplete = incomplete or bool(missing_covers) or bool(missing_fields)
    return 1 if args.strict and incomplete else 0


if __name__ == "__main__":
    raise SystemExit(main())

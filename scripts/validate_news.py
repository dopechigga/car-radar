#!/usr/bin/env python3
"""Validate the published daily automotive news quota and source links."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=ROOT / "dist" / "data" / "hotspots.json")
    parser.add_argument("--config", type=Path, default=ROOT / "config" / "news-collection.json")
    args = parser.parse_args()
    data = json.loads(args.data.read_text(encoding="utf-8"))
    config = json.loads(args.config.read_text(encoding="utf-8"))
    events = [item for item in data.get("items", []) if item.get("type") == "event"]
    invalid = [
        item.get("id", "<missing-id>")
        for item in events
        if not item.get("title") or not item.get("sources") or not all(source.get("url") for source in item["sources"])
    ]
    minimum = int(config["dailyMinimum"])
    print(f"Automotive news: {len(events)} / {minimum} minimum")
    print(f"News without usable title/source: {len(invalid)}")
    return 1 if len(events) < minimum or invalid else 0


if __name__ == "__main__":
    raise SystemExit(main())

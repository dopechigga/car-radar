#!/usr/bin/env python3
"""Publish the latest automotive event snapshot without touching Top Cases."""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "dist" / "data" / "hotspots.json"
SNAPSHOT_FILE = ROOT / "data" / "staging" / "events.json"
LAST_GOOD_FILE = ROOT / "data" / "last_good" / "hotspots.json"
TZ = ZoneInfo("Asia/Shanghai")

REQUIRED = {
    "id", "type", "category", "hot", "create", "time", "timeText",
    "eventDate", "status", "brands", "models", "title", "summary",
    "keyFact", "why", "points", "angles", "sources",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def validate(snapshot: dict) -> list[dict]:
    if snapshot.get("status") != "ok":
        raise ValueError("event snapshot status is not ok")
    events = snapshot.get("items")
    if not isinstance(events, list) or not events:
        raise ValueError("event snapshot is empty")
    seen: set[str] = set()
    for event in events:
        missing = REQUIRED.difference(event)
        if missing:
            raise ValueError(f"{event.get('id', 'unknown')} missing fields: {sorted(missing)}")
        if event["type"] != "event":
            raise ValueError(f"{event['id']} is not an event")
        if event["id"] in seen:
            raise ValueError(f"duplicate event id: {event['id']}")
        if not event["sources"] or not all(source.get("url") for source in event["sources"]):
            raise ValueError(f"{event['id']} has no usable source")
        seen.add(event["id"])
    return events


def main() -> int:
    current = read_json(DATA_FILE)
    snapshot = read_json(SNAPSHOT_FILE)
    events = validate(snapshot)
    cases = [item for item in current.get("items", []) if item.get("type") == "case"]
    now = datetime.now(TZ)

    output = dict(current)
    output["items"] = events + cases
    output["generatedAt"] = now.isoformat(timespec="seconds")
    output["nextUpdate"] = (now + timedelta(days=1)).replace(
        hour=9, minute=0, second=0, microsecond=0
    ).isoformat()
    output["hotspotRefreshStatus"] = {
        "state": "updated",
        "fresh": len(events),
        "snapshot": str(SNAPSHOT_FILE.relative_to(ROOT)),
        "collectedAt": snapshot.get("collectedAt", now.isoformat(timespec="seconds")),
    }
    policy = dict(output.get("topCasePolicy", {}))
    policy["cadenceHours"] = 24
    policy["cadenceLabel"] = "每天更新一次"
    output["topCasePolicy"] = policy

    ids = [item["id"] for item in output["items"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate item ids after event refresh")

    LAST_GOOD_FILE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DATA_FILE, LAST_GOOD_FILE)
    atomic_json_write(DATA_FILE, output)
    print(f"Published {len(events)} fresh automotive events; preserved {len(cases)} Top Cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

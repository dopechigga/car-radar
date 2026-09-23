#!/usr/bin/env python3
"""Best-effort cloud collection for the three social platforms.

Public social pages frequently require login, browser JavaScript, or a risk
challenge. The cloud run probes every platform and accepts a structured
collector URL when one is configured. A failed platform never overwrites its
last valid snapshot; the publisher then keeps that platform's last-good cases.
"""

from __future__ import annotations

import json
import os
import ssl
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "data" / "staging"
STATUS_FILE = STAGING / "social-cloud-status.json"
TZ = ZoneInfo("Asia/Shanghai")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
SYSTEM_CA = Path("/etc/ssl/cert.pem")
SSL_CONTEXT = ssl.create_default_context(cafile=str(SYSTEM_CA)) if SYSTEM_CA.exists() else ssl.create_default_context()
PLATFORMS = {
    "微博": ("weibo", "https://s.weibo.com/weibo?q=%E6%B1%BD%E8%BD%A6"),
    "小红书": ("xiaohongshu", "https://www.xiaohongshu.com/search_result?keyword=%E6%B1%BD%E8%BD%A6"),
    "抖音": ("douyin", "https://www.douyin.com/search/%E6%B1%BD%E8%BD%A6"),
}
REQUIRED = {"externalId", "title", "author", "cover", "source"}


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=25, context=SSL_CONTEXT) as response:
        return json.loads(response.read().decode("utf-8"))


def probe(url: str) -> tuple[int, int]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(request, timeout=20, context=SSL_CONTEXT) as response:
        body = response.read(32768)
        return int(response.status), len(body)


def validate_payload(platform: str, payload: dict) -> None:
    if payload.get("status") != "ok" or payload.get("platform") != platform:
        raise ValueError("collector payload status/platform mismatch")
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("collector returned no items")
    valid = [item for item in items if REQUIRED.issubset(item) and all(item.get(key) for key in REQUIRED)]
    if not valid:
        raise ValueError("collector returned no complete items")


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    now = datetime.now(TZ)
    statuses: dict[str, dict] = {}
    for platform, (slug, public_url) in PLATFORMS.items():
        collector_url = os.environ.get(f"{slug.upper()}_COLLECTOR_URL", "").strip()
        if collector_url:
            try:
                payload = fetch_json(collector_url)
                validate_payload(platform, payload)
                atomic_write(STAGING / f"{slug}.json", payload)
                statuses[platform] = {"state": "updated", "mode": "structured-collector", "items": len(payload["items"])}
                continue
            except Exception as exc:
                statuses[platform] = {"state": "last-good", "mode": "structured-collector", "reason": str(exc)}
                continue
        try:
            status, size = probe(public_url)
            statuses[platform] = {
                "state": "last-good",
                "mode": "public-page-probe",
                "reason": "公开页可达，但云端没有登录态，保留上一版并等待本机登录后补采",
                "httpStatus": status,
                "sampleBytes": size,
            }
        except Exception as exc:
            statuses[platform] = {
                "state": "last-good",
                "mode": "public-page-probe",
                "reason": f"公开页采集失败，保留上一版：{type(exc).__name__}",
            }
    atomic_write(
        STATUS_FILE,
        {"collectedAt": now.isoformat(timespec="seconds"), "platforms": statuses},
    )
    for platform, status in statuses.items():
        print(f"- {platform}: {status['state']} ({status['mode']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Merge collector snapshots into the dashboard and publish atomically.

Collectors only need to write ``data/staging/<platform>.json``.  This script
handles normalization, automotive filtering, deduplication, quota filling,
last-good fallback and the final atomic replace.
"""

from __future__ import annotations

import json
import math
import re
import shutil
import tempfile
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = ROOT / "config" / "topcase-collection.json"
DATA_FILE = ROOT / "dist" / "data" / "hotspots.json"
STAGING_DIR = ROOT / "data" / "staging"
LAST_GOOD_FILE = ROOT / "data" / "last_good" / "hotspots.json"
TZ = ZoneInfo("Asia/Shanghai")

BRAND_TERMS = [
    "小米", "小鹏", "理想", "蔚来", "比亚迪", "方程豹", "启境", "长安", "岚图",
    "享界", "问界", "极氪", "领克", "大众", "奥迪", "宝马", "奔驰", "特斯拉",
    "雷克萨斯", "保时捷", "丰田", "福特", "阿维塔", "智己", "奇瑞", "吉利",
]
MODEL_TERMS = [
    "N90", "SU7", "YU7", "G9L", "GX7", "Q06", "方程S", "梦想家9", "G9", "大汉",
    "ES8", "i9", "i8", "i6", "Model 3", "F-150", "A4L", "Q5L", "718", "T6",
]
AUTOMOTIVE_TERMS = BRAND_TERMS + MODEL_TERMS + [
    "汽车", "新车", "车型", "车主", "轿车", "SUV", "MPV", "智驾", "续航", "充电",
    "电池", "试驾", "拆车", "提车", "用车", "车展", "上市", "发布会", "底盘", "增程", "纯电", "销量",
]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def is_automotive(record: dict) -> bool:
    haystack = " ".join(str(record.get(key, "")) for key in ("title", "summary", "author"))
    return any(term.lower() in haystack.lower() for term in AUTOMOTIVE_TERMS)


def age_minutes(label: str) -> int:
    if "分钟" in label:
        match = re.search(r"(\d+)分钟", label)
        return int(match.group(1)) if match else 30
    if "小时" in label:
        match = re.search(r"(\d+)小时", label)
        return (int(match.group(1)) if match else 1) * 60
    if "昨天" in label or "1天前" in label:
        return 1440
    if "前天" in label:
        return 2880
    match = re.search(r"(\d+)天前", label)
    if match:
        return int(match.group(1)) * 1440
    if "1周前" in label:
        return 10080
    return 10080


def entities(title: str) -> tuple[list[str], list[str]]:
    brands = [term for term in BRAND_TERMS if term.lower() in title.lower()]
    models = [term for term in MODEL_TERMS if term.lower() in title.lower()]
    return brands or ["汽车行业"], models


def normalize(platform: str, record: dict, now: datetime) -> dict:
    external_id = str(record["externalId"])
    title = str(record["title"]).strip()
    author = str(record["author"]).strip()
    date_label = str(record.get("dateLabel") or "近7天")
    likes = int(record.get("likes") or 0)
    engagement = str(record.get("engagement") or f"{likes:,}赞")
    brands, models = entities(title)
    hot = min(99, max(70, round(68 + math.log10(max(likes, 1) + 1) * 6)))
    content_format = str(record.get("contentFormat") or ("视频封面" if platform == "抖音" else "图文"))
    return {
        "id": f"{platform.lower()}-{external_id}",
        "type": "case",
        "platform": platform,
        "category": ["爆款 Case", "近7日高互动"],
        "hot": hot,
        "create": max(74, hot - 1),
        "time": age_minutes(date_label),
        "timeText": "24小时优先 · 不足回溯近7日",
        "eventDate": date_label,
        "status": "公开列表已核验",
        "author": author,
        "engagement": engagement,
        "engagementScore": likes,
        "brands": brands,
        "models": models,
        "title": f"{platform}爆款｜{title}",
        "summary": f"{author}发布的{content_format}案例，围绕“{title}”形成当周公开互动。",
        "keyFact": engagement,
        "why": "按平台近7日公开搜索结果筛选，并优先保留互动量更高、指向具体车型或事件的内容。",
        "points": [f"发布时间：{date_label}", f"公开互动：{engagement}", f"内容形态：{content_format}"],
        "angles": [f"围绕“{title}”提炼事实型选题", "结合评论区继续拆解用户关注与争议点"],
        "sources": [{"name": f"{platform}｜{author} 原内容", "publishedAt": date_label, "url": record["source"]}],
        "contentFormat": content_format,
        "cover": record["cover"],
        "sourceCover": record["cover"],
        "coverAlt": title,
        "coverStatus": "已采集",
        "collectedDate": now.date().isoformat(),
    }


def validate_snapshot(platform: str, snapshot: dict) -> list[dict]:
    if snapshot.get("status") != "ok" or snapshot.get("platform") != platform:
        raise ValueError("snapshot status or platform mismatch")
    collected_at = str(snapshot.get("collectedAt") or "")
    if not collected_at:
        raise ValueError("snapshot has no collectedAt")
    collected = datetime.fromisoformat(collected_at.replace("Z", "+00:00"))
    if collected.tzinfo is None:
        collected = collected.replace(tzinfo=TZ)
    if datetime.now(TZ) - collected.astimezone(TZ) > timedelta(hours=36):
        raise ValueError("snapshot is older than 36 hours")
    required = {"externalId", "title", "author", "cover", "source"}
    valid: list[dict] = []
    seen: set[str] = set()
    for record in snapshot.get("items", []):
        if not required.issubset(record) or not all(record.get(field) for field in required):
            continue
        key = str(record["externalId"])
        if key in seen or not is_automotive(record):
            continue
        seen.add(key)
        valid.append(record)
    if not valid:
        raise ValueError("snapshot contains no valid automotive records")
    return valid


def main() -> int:
    config = read_json(CONFIG_FILE)
    current = read_json(DATA_FILE)
    quota = int(config["dailyQuotaPerPlatform"])
    now = datetime.now(TZ)
    non_cases = [item for item in current.get("items", []) if item.get("type") != "case"]
    current_by_platform = {
        platform: [
            item for item in current.get("items", [])
            if item.get("type") == "case" and item.get("platform") == platform
        ]
        for platform in config["platforms"]
    }

    merged_cases: list[dict] = []
    refresh_status: dict[str, dict] = {}
    cloud_status_path = STAGING_DIR / "social-cloud-status.json"
    cloud_report = read_json(cloud_status_path) if cloud_status_path.exists() else {}
    cloud_status = cloud_report.get("platforms", {})
    cloud_checked_at = str(cloud_report.get("collectedAt") or "")
    for platform in config["platforms"]:
        snapshot_path = STAGING_DIR / f"{platform}.json"
        if not snapshot_path.exists():
            romanized = {"微博": "weibo", "小红书": "xiaohongshu", "抖音": "douyin"}[platform]
            snapshot_path = STAGING_DIR / f"{romanized}.json"
        previous = current_by_platform[platform]
        try:
            snapshot = read_json(snapshot_path)
            platform_cloud_status = cloud_status.get(platform, {})
            if platform_cloud_status.get("state") == "last-good" and cloud_checked_at:
                snapshot_time = datetime.fromisoformat(str(snapshot.get("collectedAt", "")).replace("Z", "+00:00"))
                checked_time = datetime.fromisoformat(cloud_checked_at.replace("Z", "+00:00"))
                if snapshot_time.tzinfo is None:
                    snapshot_time = snapshot_time.replace(tzinfo=TZ)
                if checked_time.tzinfo is None:
                    checked_time = checked_time.replace(tzinfo=TZ)
                if snapshot_time <= checked_time:
                    raise ValueError("cloud attempt did not produce a fresh authenticated snapshot")
            raw = validate_snapshot(platform, snapshot)
            fresh = [normalize(platform, record, now) for record in raw]
            fresh.sort(key=lambda item: (int(item.get("engagementScore", 0)), -int(item.get("time", 10080))), reverse=True)
            fresh_ids = {item["id"] for item in fresh}
            fallback = [item for item in previous if item.get("id") not in fresh_ids]
            selected = (fresh + fallback)[:quota]
            merged_cases.extend(selected)
            refresh_status[platform] = {
                "state": "updated",
                "fresh": min(len(fresh), quota),
                "fallback": max(0, len(selected) - min(len(fresh), quota)),
                "total": len(selected),
                "snapshot": str(snapshot_path.relative_to(ROOT)),
            }
        except Exception as exc:  # last-good fallback is intentional here
            selected = previous[:quota]
            merged_cases.extend(selected)
            cloud_reason = cloud_status.get(platform, {}).get("reason")
            refresh_status[platform] = {
                "state": "last-good",
                "fresh": 0,
                "fallback": len(selected),
                "total": len(selected),
                "reason": cloud_reason or str(exc),
            }

    output = dict(current)
    output["items"] = non_cases + merged_cases
    output["generatedAt"] = now.isoformat(timespec="seconds")
    output["nextUpdate"] = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0).isoformat()
    output["refreshStatus"] = refresh_status

    ids = [item.get("id") for item in output["items"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate item ids after merge")
    if DATA_FILE.exists():
        LAST_GOOD_FILE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DATA_FILE, LAST_GOOD_FILE)
    atomic_json_write(DATA_FILE, output)

    counts = Counter(item.get("platform") for item in merged_cases)
    print(f"Published {len(output['items'])} dashboard items atomically")
    for platform in config["platforms"]:
        state = refresh_status[platform]["state"]
        print(f"- {platform}: {counts[platform]}/{quota} ({state})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

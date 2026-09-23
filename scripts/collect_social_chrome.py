#!/usr/bin/env python3
"""Collect social cases through the user's existing, logged-in Google Chrome.

Chrome opens temporary search tabs in the existing profile, returns public DOM
data through AppleScript, and closes the tabs after each query. No cookies or
credentials are read, copied, serialized, or committed.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "data" / "staging"
STATUS_FILE = STAGING / "social-local-status.json"
TZ = ZoneInfo("Asia/Shanghai")
MIN_ITEMS = int(os.environ.get("CAR_RADAR_LOCAL_MIN_ITEMS", "5"))
MAX_ITEMS = 45

AUTOMOTIVE_TERMS = [
    "汽车", "新车", "车型", "车主", "轿车", "越野", "皮卡", "SUV", "MPV", "智驾", "自动驾驶",
    "辅助驾驶", "续航", "充电", "电池", "试驾", "拆车", "提车", "用车", "车展", "上市", "发布会",
    "底盘", "增程", "纯电", "插混", "比亚迪", "方程豹", "腾势", "仰望", "吉利", "银河", "极氪",
    "领克", "奇瑞", "长安", "启源", "深蓝", "阿维塔", "蔚来", "理想", "小鹏", "小米汽车", "问界",
    "智界", "享界", "岚图", "零跑", "智己", "宝马", "奔驰", "奥迪", "特斯拉", "大众", "丰田",
    "本田", "日产", "保时捷", "福特", "红旗", "坦克", "哈弗", "五菱",
]

PLATFORMS = [
    {
        "name": "微博", "slug": "weibo", "format": "图文",
        "pattern": r"weibo\.com\/(?:detail\/|\d+\/)[A-Za-z0-9]+",
        "urls": [f"https://s.weibo.com/weibo?q={quote(query)}&Refer=index" for query in ["汽车 新车", "汽车 上市", "新能源汽车", "智能驾驶"]],
    },
    {
        "name": "小红书", "slug": "xiaohongshu", "format": "图文",
        "pattern": r"xiaohongshu\.com\/(?:explore|discovery\/item)\/[a-z0-9]+",
        "urls": [f"https://www.xiaohongshu.com/search_result?keyword={quote(query)}&source=web_search_result_notes" for query in ["汽车 新车", "新能源车", "智能驾驶", "试驾"]],
    },
    {
        "name": "抖音", "slug": "douyin", "format": "视频封面",
        "pattern": r"douyin\.com\/video\/\d+",
        "urls": [f"https://www.douyin.com/search/{quote(query)}?type=video" for query in ["汽车 新车", "新能源汽车", "智能驾驶", "试驾"]],
    },
]

APPLE_SCRIPT = r'''
on run argv
  set targetURL to item 1 of argv
  set jsCode to item 2 of argv
  tell application "Google Chrome"
    if (count of windows) is 0 then make new window
    set targetWindow to front window
    set collectorTab to make new tab at end of tabs of targetWindow with properties {URL:targetURL}
    delay 4
    repeat with i from 1 to 4
      try
        execute collectorTab javascript "window.scrollBy(0, 1800); true"
      end try
      delay 1
    end repeat
    try
      set payload to execute collectorTab javascript jsCode
      close collectorTab
      return payload
    on error errorMessage number errorNumber
      try
        close collectorTab
      end try
      error errorMessage number errorNumber
    end try
  end tell
end run
'''


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def extraction_js(pattern: str) -> str:
    terms = json.dumps(AUTOMOTIVE_TERMS, ensure_ascii=False)
    pattern_literal = json.dumps(pattern)
    return f'''(() => {{
      const pattern = new RegExp({pattern_literal}, 'i');
      const terms = {terms};
      const abs = href => {{ try {{ return new URL(href, location.href).toString(); }} catch {{ return ''; }} }};
      const rows = [];
      for (const anchor of document.querySelectorAll('a[href]')) {{
        const source = abs(anchor.getAttribute('href'));
        if (!pattern.test(source)) continue;
        let container = anchor;
        for (let i=0; i<5 && container.parentElement; i++) {{
          const next = container.parentElement;
          if ((next.innerText || '').length > 700) break;
          container = next;
        }}
        const text = (container.innerText || anchor.innerText || '').trim();
        if (!terms.some(term => text.toLowerCase().includes(term.toLowerCase()))) continue;
        const img = container.querySelector('img') || anchor.querySelector('img');
        const cover = img ? (img.currentSrc || img.src || img.getAttribute('data-src') || '') : '';
        const authorNode = container.querySelector('[class*="author"], [class*="name"], [class*="user"], [data-e2e*="author"]');
        rows.push({{source, text, cover, author: authorNode ? authorNode.textContent.trim() : ''}});
      }}
      return JSON.stringify(rows);
    }})()'''


def chrome_extract(url: str, pattern: str) -> list[dict]:
    result = subprocess.run(
        ["osascript", "-", url, extraction_js(pattern)],
        input=APPLE_SCRIPT,
        text=True,
        capture_output=True,
        timeout=75,
        check=False,
    )
    if result.returncode:
        message = (result.stderr or result.stdout).strip()
        if "AppleScript 执行 JavaScript" in message or "JavaScript from Apple Events" in message:
            raise RuntimeError("Chrome 尚未开启“允许 Apple 事件中的 JavaScript”")
        raise RuntimeError(message[-300:] or f"osascript exited {result.returncode}")
    try:
        payload = json.loads(result.stdout.strip() or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError("Chrome 返回的数据无法解析") from exc
    return payload if isinstance(payload, list) else []


def canonical_url(raw: str) -> str:
    try:
        parts = urlsplit(raw)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    except ValueError:
        return ""


def parse_count(text: str) -> int:
    match = re.search(r"(\d+(?:\.\d+)?)\s*万\s*(?:赞|点赞|喜欢|获赞)?", text)
    if match:
        return round(float(match.group(1)) * 10000)
    match = re.search(r"(\d[\d,]*)\s*(?:赞|点赞|喜欢|获赞)", text)
    return int(match.group(1).replace(",", "")) if match else 0


def pick_title(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if 6 <= len(line) <= 100]
    specific = next((line for line in lines if any(term.lower() in line.lower() for term in AUTOMOTIVE_TERMS)), "")
    return (specific or (lines[0] if lines else ""))[:100]


def normalize(row: dict, platform: dict) -> dict | None:
    source = canonical_url(str(row.get("source") or ""))
    title = pick_title(str(row.get("text") or ""))
    cover = urljoin(source, str(row.get("cover") or ""))
    if not source or not title or not cover.startswith("http"):
        return None
    external_id = hashlib.sha1(source.encode("utf-8")).hexdigest()[:18]
    text = str(row.get("text") or "")
    likes = parse_count(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    author = str(row.get("author") or "").strip()
    if not author:
        author = next((line for line in lines if line != title and len(line) < 30), "公开账号")
    return {
        "externalId": external_id,
        "title": title,
        "author": author[:40],
        "dateLabel": "近24小时",
        "likes": likes,
        "engagement": f"{likes:,}赞" if likes else "公开互动可见",
        "contentFormat": platform["format"],
        "cover": cover,
        "source": source,
    }


def collect_platform(platform: dict) -> list[dict]:
    found: dict[str, dict] = {}
    for url in platform["urls"]:
        for row in chrome_extract(url, platform["pattern"]):
            record = normalize(row, platform)
            if not record:
                continue
            previous = found.get(record["externalId"])
            if not previous or record["likes"] > previous["likes"]:
                found[record["externalId"]] = record
        if len(found) >= MAX_ITEMS:
            break
    return sorted(found.values(), key=lambda item: item["likes"], reverse=True)[:MAX_ITEMS]


def main() -> int:
    now = datetime.now(TZ).isoformat(timespec="seconds")
    statuses: dict[str, dict] = {}
    updated = 0
    for platform in PLATFORMS:
        try:
            items = collect_platform(platform)
            if len(items) < MIN_ITEMS:
                raise RuntimeError(f"只得到 {len(items)} 条可用内容，低于安全发布门槛 {MIN_ITEMS}")
            atomic_write(
                STAGING / f"{platform['slug']}.json",
                {
                    "platform": platform["name"],
                    "collectedAt": now,
                    "status": "ok",
                    "window": "近24小时优先，搜索不足时由发布层用旧 Case 补齐",
                    "collector": "existing-chrome",
                    "items": items,
                },
            )
            statuses[platform["name"]] = {"state": "updated", "items": len(items)}
            updated += 1
        except Exception as exc:
            statuses[platform["name"]] = {"state": "last-good", "reason": str(exc)}
        status = statuses[platform["name"]]
        print(f"{platform['name']}: {status['state']}" + (f" ({status['items']})" if status.get("items") else ""))
    atomic_write(STATUS_FILE, {"collectedAt": now, "platforms": statuses})
    return 0 if updated else 2


if __name__ == "__main__":
    raise SystemExit(main())

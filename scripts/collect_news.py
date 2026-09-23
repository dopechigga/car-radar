#!/usr/bin/env python3
"""Collect a daily, source-linked automotive news snapshot.

The collector intentionally uses public RSS/JSON endpoints and Python's
standard library so it can run for free in GitHub Actions. It first requests
the latest 24 hours. Only when that pool is smaller than the configured daily
minimum does it expand to the recent fallback window.
"""

from __future__ import annotations

import email.utils
import difflib
import hashlib
import html
import json
import re
import ssl
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = ROOT / "config" / "news-collection.json"
OUTPUT_FILE = ROOT / "data" / "staging" / "events.json"
TZ = ZoneInfo("Asia/Shanghai")
USER_AGENT = "Mozilla/5.0 (compatible; CarRadar/1.0; +https://github.com/dopechigga/car-radar)"
SYSTEM_CA = Path("/etc/ssl/cert.pem")
SSL_CONTEXT = ssl.create_default_context(cafile=str(SYSTEM_CA)) if SYSTEM_CA.exists() else ssl.create_default_context()

CORE_TERMS = [
    "汽车", "新车", "车型", "车企", "车主", "轿车", "跑车", "越野车", "皮卡",
    "SUV", "MPV", "智驾", "自动驾驶", "辅助驾驶", "续航", "充电", "电池", "油耗",
    "车展", "上市", "预售", "交付", "召回", "碰撞", "底盘", "发动机", "插混", "增程", "纯电",
]
BRANDS = [
    "比亚迪", "方程豹", "仰望", "腾势", "吉利", "银河", "极氪", "领克", "奇瑞", "星途",
    "捷途", "长安", "启源", "深蓝", "阿维塔", "蔚来", "乐道", "萤火虫", "理想", "小鹏",
    "小米汽车", "问界", "智界", "享界", "尊界", "岚图", "零跑", "智己", "广汽", "传祺",
    "埃安", "上汽", "一汽", "东风", "红旗", "五菱", "宝骏", "长城", "哈弗", "坦克",
    "大众", "奥迪", "宝马", "奔驰", "保时捷", "特斯拉", "丰田", "本田", "日产", "福特",
    "沃尔沃", "雷克萨斯", "凯迪拉克", "别克", "现代", "起亚", "宾利", "法拉利", "兰博基尼",
]
EXCLUDE_TERMS = [
    "手机", "平板", "笔记本", "电视", "耳机", "家电", "游戏", "演唱会", "房地产", "股票行情",
    "摩托车", "机车", "两轮",
]
MODEL_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:Model\s?[3SXY]|[A-Z]{1,4}[ -]?\d{1,3}(?:\s?L|\s?Max|\s?Ultra|\s?Pro)?|"
    r"SU7|YU7|MEGA|秦[一-龥A-Za-z0-9]*|汉[一-龥A-Za-z0-9]*|宋[一-龥A-Za-z0-9]*|"
    r"海豹[一-龥A-Za-z0-9]*|海狮[一-龥A-Za-z0-9]*|理想[LI]\d|问界M\d|小鹏[PGX]\d+[A-Za-z]*)",
    re.IGNORECASE,
)


@dataclass
class Article:
    title: str
    url: str
    publisher: str
    published: datetime
    feed_hits: int = 1
    query_hits: set[str] = field(default_factory=set)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def fetch(url: str, timeout: int = 25) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/json, text/xml;q=0.9, */*;q=0.5"},
    )
    with urllib.request.urlopen(request, timeout=timeout, context=SSL_CONTEXT) as response:
        return response.read()


def clean_text(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    return re.sub(r"\s+", " ", value).strip()


def parse_date(value: str) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def split_google_title(title: str, source: str) -> tuple[str, str]:
    parts = title.rsplit(" - ", 1)
    if len(parts) == 2 and len(parts[1]) <= 40:
        return parts[0].strip(), source or parts[1].strip()
    return title.strip(), source


def parse_rss(data: bytes, query: str) -> list[Article]:
    root = ET.fromstring(data)
    result: list[Article] = []
    for item in root.findall(".//item"):
        title = clean_text(item.findtext("title") or "")
        link = clean_text(item.findtext("link") or "")
        source_node = item.find("source")
        source = clean_text(source_node.text if source_node is not None and source_node.text else "")
        title, source = split_google_title(title, source)
        if not title or not link:
            continue
        result.append(Article(title, link, source or "公开新闻源", parse_date(item.findtext("pubDate") or ""), query_hits={query}))
    return result


def google_rss_url(query: str, hours: int) -> str:
    search = f"{query} when:{max(1, hours // 24)}d"
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": search, "hl": "zh-CN", "gl": "CN", "ceid": "CN:zh-Hans"}
    )


def bing_rss_url(query: str) -> str:
    return "https://www.bing.com/news/search?" + urllib.parse.urlencode(
        {"q": query, "format": "rss", "setlang": "zh-cn", "cc": "cn"}
    )


def is_automotive(title: str) -> bool:
    low = title.lower()
    has_core = any(term.lower() in low for term in CORE_TERMS)
    has_brand = any(brand.lower() in low for brand in BRANDS)
    excluded = any(term.lower() in low for term in EXCLUDE_TERMS)
    if has_core:
        return True
    return has_brand and not excluded


def canonical_key(article: Article) -> str:
    title = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", article.title).lower()
    return title[:100]


def collect(queries: list[str], hours: int) -> tuple[list[Article], list[str]]:
    articles: dict[str, Article] = {}
    errors: list[str] = []
    endpoints: list[tuple[str, str]] = []
    for query in queries:
        endpoints.append((query, google_rss_url(query, hours)))
        endpoints.append((query, bing_rss_url(query)))
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    for index, (query, url) in enumerate(endpoints):
        try:
            for article in parse_rss(fetch(url), query):
                if article.published < cutoff or not is_automotive(article.title):
                    continue
                key = canonical_key(article)
                if len(key) < 8:
                    continue
                if key in articles:
                    articles[key].feed_hits += 1
                    articles[key].query_hits.update(article.query_hits)
                    if article.published > articles[key].published:
                        articles[key].published = article.published
                else:
                    articles[key] = article
        except Exception as exc:
            errors.append(f"{urllib.parse.urlparse(url).netloc}:{query}:{type(exc).__name__}")
        if index and index % 8 == 0:
            time.sleep(0.15)
    ranked = sorted(
        articles.values(),
        key=lambda article: (article.feed_hits + len(article.query_hits), article.published),
        reverse=True,
    )
    deduplicated: list[Article] = []
    normalized_titles: list[str] = []
    for article in ranked:
        normalized = canonical_key(article)
        if any(difflib.SequenceMatcher(None, normalized, previous).ratio() >= 0.86 for previous in normalized_titles):
            continue
        deduplicated.append(article)
        normalized_titles.append(normalized)
    return deduplicated, errors


def entity_lists(title: str) -> tuple[list[str], list[str]]:
    brands = [brand for brand in BRANDS if brand.lower() in title.lower()]
    models: list[str] = []
    for match in MODEL_RE.finditer(title):
        value = match.group(0).strip()
        if value and value.lower() not in {model.lower() for model in models}:
            models.append(value)
    return brands[:4] or ["汽车行业"], models[:5]


def categories(title: str, hot: int) -> list[str]:
    result = ["正在爆" if hot >= 90 else "今日热点"]
    mapping = [
        (["上市", "预售", "发布", "首发", "新车"], "新车情报"),
        (["智驾", "自动驾驶", "辅助驾驶"], "智能驾驶"),
        (["召回", "事故", "碰撞", "安全"], "车辆安全"),
        (["销量", "交付", "财报", "市场"], "行业数据"),
        (["电池", "充电", "续航", "补能"], "补能与续航"),
        (["政策", "标准", "监管"], "政策动态"),
    ]
    for terms, label in mapping:
        if any(term in title for term in terms):
            result.append(label)
    return result[:4]


def to_event(article: Article, rank: int, now: datetime, primary_hours: int) -> dict:
    published = article.published.astimezone(TZ)
    age = max(0, int((now - published).total_seconds() // 60))
    brands, models = entity_lists(article.title)
    is_today = age <= primary_hours * 60
    signals = article.feed_hits + len(article.query_hits)
    hot = max(70, min(99, 92 - min(age // 180, 16) + min(signals * 2, 7) - rank // 25))
    publisher = article.publisher or urllib.parse.urlparse(article.url).netloc
    date_text = published.strftime("%m月%d日 %H:%M")
    window = "24 小时内" if is_today else "近 72 小时回补"
    digest = hashlib.sha1((article.url + article.title).encode("utf-8")).hexdigest()[:14]
    return {
        "id": f"news-{digest}",
        "type": "event",
        "category": categories(article.title, hot),
        "hot": hot,
        "create": max(72, hot - 2),
        "time": age,
        "timeText": window,
        "eventDate": date_text,
        "status": "公开新闻源已采集",
        "brands": brands,
        "models": models,
        "title": article.title,
        "summary": f"{publisher}于{date_text}发布了这条汽车动态；标题已保留具体品牌、车型或事件信息。",
        "keyFact": f"{window} · {publisher}",
        "why": "按发布时间、跨关键词命中和多源重复信号排序，便于创作者快速判断当天选题价值。",
        "points": [
            f"来源：{publisher}",
            f"发布时间：{date_text}",
            f"热度信号：命中 {max(1, len(article.query_hits))} 个汽车主题，跨源/重复 {article.feed_hits} 次",
        ],
        "angles": ["从标题中的具体车型或事件切入，补充关键数字与背景", "对照同级车型、同类政策或品牌动作解释影响"],
        "sources": [{"name": publisher, "publishedAt": date_text, "url": article.url}],
        "collectedDate": now.date().isoformat(),
        "freshness": "today" if is_today else "recent-fallback",
    }


def main() -> int:
    config = read_json(CONFIG_FILE)
    minimum = int(config["dailyMinimum"])
    maximum = max(minimum, int(config.get("maximumItems", minimum)))
    primary_hours = int(config["primaryWindowHours"])
    fallback_hours = int(config["fallbackWindowHours"])
    queries = list(config["queries"])
    now = datetime.now(TZ)

    primary, errors = collect(queries, primary_hours)
    window_hours = primary_hours
    articles = primary
    if len(articles) < minimum:
        articles, fallback_errors = collect(queries, fallback_hours)
        errors.extend(fallback_errors)
        window_hours = fallback_hours

    if len(articles) < minimum:
        print(
            f"News collection produced {len(articles)} valid automotive items; {minimum} required. "
            "Existing published data was left untouched.",
            file=sys.stderr,
        )
        if errors:
            print("Source errors: " + "; ".join(errors[:12]), file=sys.stderr)
        return 1

    selected = articles[:maximum]
    items = [to_event(article, index, now, primary_hours) for index, article in enumerate(selected)]
    today_count = sum(item["freshness"] == "today" for item in items)
    payload = {
        "status": "ok",
        "collectedAt": now.isoformat(timespec="seconds"),
        "windowHours": window_hours,
        "minimum": minimum,
        "fresh24h": today_count,
        "sourceErrors": errors,
        "items": items,
    }
    atomic_write(OUTPUT_FILE, payload)
    print(f"Collected {len(items)} automotive news items ({today_count} within {primary_hours}h)")
    if errors:
        print(f"Completed with {len(errors)} source endpoint errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

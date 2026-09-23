#!/usr/bin/env python3
"""Cache remote Top Case covers inside ``dist`` and update the dataset."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "dist" / "data" / "hotspots.json"
COVER_ROOT = ROOT / "dist" / "assets" / "covers"
MAX_BYTES = 8 * 1024 * 1024


def extension(body: bytes) -> str:
    if body.startswith(b"RIFF") and body[8:12] == b"WEBP":
        return ".webp"
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if body.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    raise ValueError("response is not a supported image")


def download(item: dict) -> tuple[str, str | None, str | None]:
    item_id = item["id"]
    platform = str(item.get("platform", "other"))
    target_dir = COVER_ROOT / platform
    existing = next((path for path in target_dir.glob(f"{item_id}.*") if path.is_file()), None)
    if existing:
        return item_id, f"./assets/covers/{platform}/{existing.name}", None
    url = item.get("sourceCover") or item.get("cover")
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return item_id, item.get("cover"), None
    referer = "https://www.xiaohongshu.com/" if platform == "小红书" else "https://www.douyin.com/"
    try:
        curl = shutil.which("curl")
        if not curl:
            raise RuntimeError("curl is required for cover caching")
        with tempfile.NamedTemporaryFile("wb", delete=False) as download_file:
            download_path = Path(download_file.name)
        result = subprocess.run(
            [
                curl, "--location", "--fail", "--silent", "--show-error", "--max-time", "20",
                "--user-agent", "Mozilla/5.0 (compatible; CheShiRadar/1.0)",
                "--referer", referer, "--output", str(download_path), url,
            ],
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or f"curl exited {result.returncode}")
        body = download_path.read_bytes()
        download_path.unlink(missing_ok=True)
        if len(body) > MAX_BYTES:
            raise ValueError("image exceeds 8 MiB")
        suffix = extension(body)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{item_id}{suffix}"
        with tempfile.NamedTemporaryFile("wb", dir=target_dir, prefix=f".{item_id}.", delete=False) as handle:
            handle.write(body)
            temporary = Path(handle.name)
        temporary.replace(target)
        return item_id, f"./assets/covers/{platform}/{target.name}", None
    except Exception as exc:
        return item_id, item.get("cover"), str(exc)


def main() -> int:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    cases = [item for item in data.get("items", []) if item.get("type") == "case" and item.get("cover")]
    results: dict[str, tuple[str | None, str | None]] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(download, item): item["id"] for item in cases}
        for future in as_completed(futures):
            item_id, local_path, error = future.result()
            results[item_id] = (local_path, error)

    cached = 0
    failed = 0
    for item in cases:
        local_path, error = results[item["id"]]
        if local_path:
            if str(local_path).startswith("./assets/"):
                cached += 1
            item["cover"] = local_path
        if error:
            failed += 1
            item["coverStatus"] = "远程封面（本地缓存失败）"
        else:
            item["coverStatus"] = "已本地缓存"

    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Cover cache: {cached} local, {failed} failed")
    if failed:
        samples = [(item_id, error) for item_id, (_, error) in results.items() if error][:3]
        for item_id, error in samples:
            print(f"- {item_id}: {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

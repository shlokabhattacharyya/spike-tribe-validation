"""scrape TikTok metadata and download .mp4s for every video in videos.csv.

Usage:
    python scripts/02_scrape.py

Reads:
    data/videos.csv  (must have video_id, creator, vertical, url filled in)
    .env             (must contain APIFY_TOKEN=...)

Writes:
    data/raw/{video_id}.mp4   - downloaded videos
    data/videos.csv           - updated in place with all metadata fields

Idempotent: if a video's mp4 exists AND its CSV row is fully populated, it's skipped.
Re-run safely after partial failures.
"""
import csv
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests
from apify_client import ApifyClient
from dotenv import load_dotenv

# ---------- config ----------
PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "videos.csv"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
ACTOR_ID = "clockworks/tiktok-scraper"
DOWNLOAD_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/120.0.0.0 Safari/537.36"}
DOWNLOAD_TIMEOUT = 60
DOWNLOAD_RETRIES = 3
SLEEP_BETWEEN_DOWNLOADS = 0.5  # be polite to TikTok's CDN

# columns that the scraper fills in (everything except the 4 user-set fields)
SCRAPED_COLUMNS = [
    "label",
    "views_at_24h",
    "views_at_7d",
    "views_at_30d",
    "post_timestamp",
    "caption",
    "hashtags",
    "music_id",
    "duration",
    "creator_followers_at_post",
    "creator_avg_views_trailing_30d",
]


def load_env():
    load_dotenv(PROJECT_ROOT / ".env")
    token = os.getenv("APIFY_TOKEN")
    if not token:
        sys.exit("APIFY_TOKEN not found in .env. Set it and retry.")
    return token


def read_csv():
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames


def write_csv(rows, fieldnames):
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def is_row_complete(row):
    """A row is complete when scraped fields are filled and mp4 is on disk."""
    mp4_exists = (RAW_DIR / f"{row['video_id']}.mp4").exists()
    fields_filled = bool(row.get("caption", "").strip() or row.get("duration", "").strip())
    return mp4_exists and fields_filled


def hashtags_from_item(item):
    """Extract hashtags as a comma-separated string. Apify uses 'hashtags' or names embedded in text."""
    tags = item.get("hashtags") or []
    if isinstance(tags, list):
        names = [t.get("name", "") if isinstance(t, dict) else str(t) for t in tags]
        return ",".join(n for n in names if n)
    return str(tags) if tags else ""


def fetch_videos_for_urls(client, urls):
    """One Apify call for a batch of video URLs. Returns dict {video_id: item}."""
    print(f"  Calling Apify for {len(urls)} URLs...")
    run_input = {
        "postURLs": urls,
        "shouldDownloadVideos": False,  # we'll download .mp4s ourselves
        "shouldDownloadCovers": False,
        "shouldDownloadSubtitles": False,
        "resultsPerPage": len(urls),
    }
    run = client.actor(ACTOR_ID).call(run_input=run_input)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    print(f"  Got {len(items)} items back from Apify")

    by_id = {}
    for item in items:
        vid = str(item.get("id") or "").strip()
        if vid:
            by_id[vid] = item
    return by_id


def fetch_creator_avg_views(client, creator):
    """Fetch creator's recent videos and average view counts. Returns float or empty string."""
    try:
        run_input = {
            "profiles": [creator],
            "resultsPerPage": 30,
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
            "shouldDownloadSubtitles": False,
        }
        run = client.actor(ACTOR_ID).call(run_input=run_input)
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        if not items:
            return ""
        views = [int(it.get("playCount", 0) or 0) for it in items if it.get("playCount") is not None]
        views = [v for v in views if v > 0]
        if not views:
            return ""
        return round(sum(views) / len(views), 1)
    except Exception as e:
        print(f"    creator avg views fetch failed for {creator}: {e}")
        return ""


def populate_row_from_item(row, item):
    """Fill in scraped CSV fields from the Apify item dict."""
    play_count = item.get("playCount") or 0
    duration = item.get("videoMeta", {}).get("duration") or item.get("duration") or ""
    music_id = (item.get("musicMeta") or {}).get("musicId") or ""
    caption = (item.get("text") or "").replace("\n", " ").strip()
    timestamp = item.get("createTimeISO") or item.get("createTime") or ""
    creator_meta = item.get("authorMeta") or {}
    followers = creator_meta.get("fans") or creator_meta.get("followers") or ""

    # views: lifetime (= ~30d for settled videos in our dataset)
    row["views_at_30d"] = str(play_count) if play_count else ""
    row["views_at_24h"] = ""  # not reliably retrievable retroactively
    row["views_at_7d"] = ""   # not reliably retrievable retroactively

    row["caption"] = caption
    row["hashtags"] = hashtags_from_item(item)
    row["music_id"] = str(music_id) if music_id else ""
    row["duration"] = str(duration) if duration else ""
    row["post_timestamp"] = str(timestamp) if timestamp else ""
    row["creator_followers_at_post"] = str(followers) if followers else ""

    # label per memo's thresholds
    if play_count > 1_000_000:
        row["label"] = "viral"
    elif play_count < 50_000:
        row["label"] = "dud"
    else:
        row["label"] = "mid"


def download_mp4(url, out_path):
    """Download a single .mp4 with retries. Returns True on success, False on failure."""
    if out_path.exists() and out_path.stat().st_size > 100_000:
        return True  # already downloaded and looks reasonable
    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        try:
            r = requests.get(url, headers=DOWNLOAD_HEADERS, timeout=DOWNLOAD_TIMEOUT, stream=True)
            r.raise_for_status()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        f.write(chunk)
            if out_path.stat().st_size < 100_000:
                raise IOError(f"downloaded file too small ({out_path.stat().st_size} bytes)")
            return True
        except Exception as e:
            print(f"    download attempt {attempt} failed: {e}")
            if attempt < DOWNLOAD_RETRIES:
                time.sleep(2 ** attempt)
    return False


def main():
    token = load_env()
    client = ApifyClient(token)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    rows, fieldnames = read_csv()
    print(f"Loaded {len(rows)} rows from {CSV_PATH}")

    # Skip already-complete rows
    todo = [r for r in rows if not is_row_complete(r)]
    print(f"{len(todo)} rows need scraping/downloading ({len(rows) - len(todo)} already complete)")
    if not todo:
        print("Everything already complete. Done.")
        return

    # Step 1: batch-fetch metadata for all incomplete rows in one Apify call
    urls = [r["url"] for r in todo]
    items_by_id = fetch_videos_for_urls(client, urls)

    # Step 2: populate metadata fields
    missing_metadata = []
    for row in todo:
        item = items_by_id.get(row["video_id"])
        if item is None:
            print(f"  no Apify result for {row['video_id']} ({row['creator']})")
            missing_metadata.append(row["video_id"])
            continue
        populate_row_from_item(row, item)
        # remember the video CDN URL for downloading
        row["_download_url"] = (
            item.get("videoMeta", {}).get("downloadAddr")
            or item.get("videoUrl")
            or item.get("webVideoUrl")
            or ""
        )

    # Step 3: per-creator avg views (one call per unique creator)
    unique_creators = sorted({r["creator"] for r in todo})
    print(f"\nFetching trailing avg views for {len(unique_creators)} creators...")
    creator_avgs = {}
    for i, creator in enumerate(unique_creators, 1):
        print(f"  [{i}/{len(unique_creators)}] {creator}")
        creator_avgs[creator] = fetch_creator_avg_views(client, creator)
    for row in todo:
        row["creator_avg_views_trailing_30d"] = str(creator_avgs.get(row["creator"], ""))

    # Step 4: write CSV before downloads start (so a download crash doesn't lose metadata)
    for row in rows:
        row.pop("_download_url", None) if False else None
    rows_for_save = [{k: v for k, v in r.items() if k in fieldnames} for r in rows]
    write_csv(rows_for_save, fieldnames)
    print(f"\nMetadata saved to {CSV_PATH}")

    # Step 5: download .mp4s
    print(f"\nDownloading {len(todo)} .mp4 files...")
    fails = []
    for i, row in enumerate(todo, 1):
        out_path = RAW_DIR / f"{row['video_id']}.mp4"
        download_url = row.get("_download_url", "")
        if not download_url:
            print(f"  [{i}/{len(todo)}] {row['video_id']} - no download URL, skipping")
            fails.append(row["video_id"])
            continue
        print(f"  [{i}/{len(todo)}] {row['video_id']} ({row['vertical']}/{row['creator']})")
        ok = download_mp4(download_url, out_path)
        if not ok:
            fails.append(row["video_id"])
        time.sleep(SLEEP_BETWEEN_DOWNLOADS)

    # Summary
    print(f"\n{'='*60}")
    print(f"Done. Downloaded {len(todo) - len(fails)}/{len(todo)} videos.")
    if missing_metadata:
        print(f"Missing metadata for: {missing_metadata}")
    if fails:
        print(f"Failed downloads for: {fails}")
    print(f"CSV: {CSV_PATH}")
    print(f"MP4s: {RAW_DIR}")


if __name__ == "__main__":
    main()

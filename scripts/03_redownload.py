"""Re-download all videos using yt-dlp from the URLs in videos.csv.

Fixed version: removes --quiet flag (was masking real errors and possibly
truncating output), adds proper sync, prints yt-dlp output for diagnostics.
"""
import csv
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "videos.csv"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
SLEEP_BETWEEN = 1.0


def is_valid_mp4(path: Path) -> bool:
    """Returns True if ffprobe can read duration from the file."""
    if not path.exists() or path.stat().st_size < 50_000:
        return False
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return False
        try:
            duration = float(result.stdout.strip())
            return duration > 0.5
        except ValueError:
            return False
    except Exception:
        return False


def download_one(url: str, out_path: Path, verbose: bool = False) -> tuple[bool, str]:
    """Download via yt-dlp. Returns (success, message)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    try:
        # Run yt-dlp WITHOUT --quiet so it can flush properly.
        # Capture stderr separately for failure diagnosis.
        proc = subprocess.run(
            ["yt-dlp",
             "--no-warnings",
             "--no-playlist",
             "-f", "best[ext=mp4]/best",
             "-o", str(out_path),
             "--socket-timeout", "30",
             "--retries", "2",
             url],
            capture_output=True, text=True, timeout=180,
        )
        if proc.returncode != 0:
            return False, f"yt-dlp exit {proc.returncode}: {proc.stderr.strip()[:200]}"

        # Force filesystem sync before validation
        os.sync()
        time.sleep(0.2)

        if not out_path.exists():
            return False, "yt-dlp claimed success but file missing"
        size_kb = out_path.stat().st_size // 1024
        if not is_valid_mp4(out_path):
            return False, f"file written ({size_kb} KB) but ffprobe failed"
        return True, f"{size_kb} KB"
    except subprocess.TimeoutExpired:
        return False, "timeout (>180s)"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def main():
    if not CSV_PATH.exists():
        sys.exit(f"CSV not found: {CSV_PATH}")
    with open(CSV_PATH) as f:
        rows = list(csv.DictReader(f))
    print(f"Loaded {len(rows)} rows from {CSV_PATH}")

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    todo = []
    already_good = 0
    for row in rows:
        vid = row["video_id"]
        out_path = RAW_DIR / f"{vid}.mp4"
        if is_valid_mp4(out_path):
            already_good += 1
            continue
        todo.append(row)

    print(f"Already valid: {already_good}")
    print(f"To download: {len(todo)}\n")

    if not todo:
        print("Nothing to do.")
        return

    succeeded, failed = [], []
    start = time.time()
    for i, row in enumerate(todo, 1):
        vid = row["video_id"]
        url = row["url"]
        out_path = RAW_DIR / f"{vid}.mp4"
        t0 = time.time()
        ok, msg = download_one(url, out_path)
        elapsed = time.time() - t0
        marker = "OK  " if ok else "FAIL"
        print(f"[{i}/{len(todo)}] {marker} {vid} ({row['vertical']}/{row['creator']}) "
              f"- {elapsed:.1f}s - {msg}")
        if ok:
            succeeded.append(vid)
        else:
            failed.append((vid, msg))
        time.sleep(SLEEP_BETWEEN)

    total = time.time() - start
    print(f"\n{'=' * 60}")
    print(f"Done in {total / 60:.1f} min")
    print(f"Succeeded: {len(succeeded)}/{len(todo)}")
    if failed:
        print(f"Failed: {len(failed)}")
        for vid, msg in failed:
            print(f"  {vid}: {msg[:150]}")


if __name__ == "__main__":
    main()

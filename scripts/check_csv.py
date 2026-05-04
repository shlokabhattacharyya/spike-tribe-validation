"""Sanity-check videos.csv after scraping. Read-only."""
import csv
from collections import Counter, defaultdict
from pathlib import Path

CSV_PATH = Path(__file__).parent.parent / "data" / "videos.csv"

with open(CSV_PATH) as f:
    rows = list(csv.DictReader(f))

print(f"Total rows: {len(rows)}\n")

print("Label distribution:")
for label, n in Counter(r["label"] for r in rows).items():
    print(f"  {label or '<empty>'}: {n}")
print()

print("Vertical x label:")
vl = defaultdict(lambda: defaultdict(int))
for r in rows:
    vl[r["vertical"]][r["label"] or "<empty>"] += 1
for v in sorted(vl):
    print(f"  {v}: {dict(vl[v])}")
print()

print("First row sample:")
r = rows[0]
sample_keys = [
    "video_id", "creator", "vertical", "label",
    "views_at_30d", "duration", "caption",
    "creator_followers_at_post", "creator_avg_views_trailing_30d",
]
for k in sample_keys:
    val = r.get(k, "")
    if k == "caption" and len(val) > 80:
        val = val[:80] + "..."
    print(f"  {k}: {val!r}")

print("\nViews distribution (lifetime, from views_at_30d):")
views = sorted(
    [int(r["views_at_30d"]) for r in rows if r.get("views_at_30d", "").strip().isdigit()]
)
if views:
    print(f"  min: {views[0]:,}")
    print(f"  median: {views[len(views) // 2]:,}")
    print(f"  max: {views[-1]:,}")
    print(f"  rows with views: {len(views)}/{len(rows)}")
else:
    print("  no view counts populated — something went wrong")

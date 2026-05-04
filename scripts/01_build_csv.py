"""Build videos.csv from the URL list.

Parses creator and video_id from each URL. The intended_label column captures
the user's a-priori expectation (viral vs not_viral) which we'll compare against
the actual label assigned post-scraping based on view-count thresholds.
"""
import re
import csv
from pathlib import Path
from collections import Counter

# (vertical, intended_label, url) tuples
ENTRIES = [
    # ===== brainrot =====
    ("brainrot", "viral", "https://www.tiktok.com/@ai_glitch0/video/7633144286996974870"),
    ("brainrot", "viral", "https://www.tiktok.com/@mrsahuur/video/7635267660724325639"),
    ("brainrot", "viral", "https://www.tiktok.com/@brhealt/video/7615769084747156749"),
    ("brainrot", "viral", "https://www.tiktok.com/@sunnycartoon01/video/7634305506642906401"),
    ("brainrot", "viral", "https://www.tiktok.com/@brainrot.stories12/video/7616012099432647950"),
    ("brainrot", "not_viral", "https://www.tiktok.com/@sir.mew7/video/7635777258237529366"),
    ("brainrot", "not_viral", "https://www.tiktok.com/@sharkquest/video/7634607467338452238"),
    ("brainrot", "not_viral", "https://www.tiktok.com/@eden.lg1/video/7635485761164414222"),
    ("brainrot", "not_viral", "https://www.tiktok.com/@bob.beer89/video/7635385732302933278"),
    ("brainrot", "not_viral", "https://www.tiktok.com/@notyourdailyposttoday/video/7628057181409086733"),

    # ===== grwm =====
    ("grwm", "viral", "https://www.tiktok.com/@samaraispinkk/video/7473614410318269742"),
    ("grwm", "viral", "https://www.tiktok.com/@only1aliya/video/7398659936827362603"),
    ("grwm", "viral", "https://www.tiktok.com/@ninersslifeee/video/7551496380510948663"),
    ("grwm", "viral", "https://www.tiktok.com/@elm0zwrld/video/7431527117202099502"),
    ("grwm", "viral", "https://www.tiktok.com/@katiefanggg/video/7634177048994483477"),
    ("grwm", "not_viral", "https://www.tiktok.com/@fleur.varley/video/7604213016212835606"),
    ("grwm", "not_viral", "https://www.tiktok.com/@honeyj.banks/video/7606080334396132630"),
    ("grwm", "not_viral", "https://www.tiktok.com/@cadyslifex/video/7531689700885564695"),
    ("grwm", "not_viral", "https://www.tiktok.com/@that0neariesgirl/video/7635792952333290765"),
    ("grwm", "not_viral", "https://www.tiktok.com/@your_bestie_vellz/video/7597289693356510494"),

    # ===== nature =====
    ("nature", "viral", "https://www.tiktok.com/@swag.oji/video/7557191926450097438"),
    ("nature", "viral", "https://www.tiktok.com/@starm0oon/video/7505856994285210911"),
    ("nature", "viral", "https://www.tiktok.com/@aj130324/video/7562469246391946510"),
    ("nature", "viral", "https://www.tiktok.com/@reedmakesvideos/video/7519635243637198111"),
    ("nature", "viral", "https://www.tiktok.com/@karlfreg/video/7614887630026689814"),
    ("nature", "not_viral", "https://www.tiktok.com/@isobelslater/video/7446879394087308576"),
    ("nature", "not_viral", "https://www.tiktok.com/@shsoph1/video/7623324047660567828"),
    ("nature", "not_viral", "https://www.tiktok.com/@littytittii/video/7555599542071217439"),
    ("nature", "not_viral", "https://www.tiktok.com/@mfin305/video/7631052169101298957"),
    ("nature", "not_viral", "https://www.tiktok.com/@notso_brights/video/7599945491740249352"),

    # ===== sports =====
    ("sports", "viral", "https://www.tiktok.com/@hoopeclipse/video/7605381802819177758"),
    ("sports", "viral", "https://www.tiktok.com/@foot_cartel/video/7630471942499306774"),
    ("sports", "viral", "https://www.tiktok.com/@alloutsports_/video/7592386378801876254"),
    ("sports", "viral", "https://www.tiktok.com/@5461ec3b/video/7592249534432972087"),
    ("sports", "viral", "https://www.tiktok.com/@foot_cartel/video/7618354753449381142"),
    ("sports", "not_viral", "https://www.tiktok.com/@radrock_072/video/7462523643025755422"),
    ("sports", "not_viral", "https://www.tiktok.com/@konstantine.bisbi/video/7564022357904362766"),
    ("sports", "not_viral", "https://www.tiktok.com/@sportsculturetok/video/7635770013005237534"),
    ("sports", "not_viral", "https://www.tiktok.com/@viralsportv1/video/7620876107037805844"),
    ("sports", "not_viral", "https://www.tiktok.com/@pur16369k1/video/7630782922005466382"),

    # ===== funny =====
    ("funny", "viral", "https://www.tiktok.com/@divine63631/video/7606219456557239583"),
    ("funny", "viral", "https://www.tiktok.com/@sae.itoshit/video/7629881326199475469"),
    ("funny", "viral", "https://www.tiktok.com/@grandmaisgone/video/7588315891822071095"),
    ("funny", "viral", "https://www.tiktok.com/@user67235684/video/7635068039649660190"),
    ("funny", "viral", "https://www.tiktok.com/@funnypets520o/video/7592554237717007647"),
    ("funny", "not_viral", "https://www.tiktok.com/@funnyyahea.usa2/video/7635751990999387405"),
    ("funny", "not_viral", "https://www.tiktok.com/@funnyuk61/video/7635746652334165279"),
    ("funny", "not_viral", "https://www.tiktok.com/@fv77746/video/7635706768554741023"),
    ("funny", "not_viral", "https://www.tiktok.com/@falcogaze/video/7635694779929611533"),
    ("funny", "not_viral", "https://www.tiktok.com/@scrollbacktt/video/7558745499927350550"),

    # ===== romcom_edits =====
    ("romcom_edits", "viral", "https://www.tiktok.com/@emiliaaeedits/video/7622414760453197063"),
    ("romcom_edits", "viral", "https://www.tiktok.com/@editsxseriesd/video/7626807895895608593"),
    ("romcom_edits", "viral", "https://www.tiktok.com/@.eeclipwze/video/7634952421554408718"),
    ("romcom_edits", "viral", "https://www.tiktok.com/@nmsaep/video/7618629140152880391"),
    ("romcom_edits", "viral", "https://www.tiktok.com/@winche3ter/video/7631387106903969027"),
    ("romcom_edits", "not_viral", "https://www.tiktok.com/@jaemochiii/video/7635796429209947422"),
    ("romcom_edits", "not_viral", "https://www.tiktok.com/@kokayxvx/video/7635805880746839309"),
    ("romcom_edits", "not_viral", "https://www.tiktok.com/@thynrz/video/7537780432264285471"),
    ("romcom_edits", "not_viral", "https://www.tiktok.com/@lyrivie/video/7557886384757869837"),
    ("romcom_edits", "not_viral", "https://www.tiktok.com/@dancingwiththeswifties/video/7625103192178576660"),

    # ===== motivation =====
    ("motivation", "viral", "https://www.tiktok.com/@lyric_hermanson/video/7615373651390631199"),
    ("motivation", "viral", "https://www.tiktok.com/@philosophizzyebelle/video/7634674913193823519"),
    ("motivation", "viral", "https://www.tiktok.com/@hadley.214/video/7628639812731342110"),
    ("motivation", "viral", "https://www.tiktok.com/@lenalifts/video/7551479096908320055"),
    ("motivation", "viral", "https://www.tiktok.com/@growthofwisdom/video/7555925156586081558"),
    ("motivation", "not_viral", "https://www.tiktok.com/@self.mindshift/video/7583478396412529922"),
    ("motivation", "not_viral", "https://www.tiktok.com/@clixrush/video/7626029164184866061"),
    ("motivation", "not_viral", "https://www.tiktok.com/@quotes.growth.mindset/video/7265188749393415470"),
    ("motivation", "not_viral", "https://www.tiktok.com/@thedailyrise.capcut/video/7582763696837922070"),
    ("motivation", "not_viral", "https://www.tiktok.com/@motivationforyou164/video/7282385892596059434"),
]

URL_RE = re.compile(r"tiktok\.com/@([^/]+)/video/(\d+)")

COLUMNS = [
    "video_id",
    "creator",
    "vertical",
    "intended_label",  # NEW: user's a-priori classification
    "url",
    "label",  # set later by scraper based on actual view counts
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

rows = []
for vertical, intended_label, url in ENTRIES:
    m = URL_RE.search(url)
    if not m:
        print(f"SKIP (couldn't parse): {url}")
        continue
    creator, video_id = m.group(1), m.group(2)
    row = {col: "" for col in COLUMNS}
    row["video_id"] = video_id
    row["creator"] = creator
    row["vertical"] = vertical
    row["intended_label"] = intended_label
    row["url"] = url
    rows.append(row)

out_path = Path(__file__).parent.parent / "data" / "videos.csv"
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(rows)

print(f"Wrote {len(rows)} rows to {out_path}\n")

print("Vertical x intended_label:")
from collections import defaultdict
vl = defaultdict(lambda: defaultdict(int))
for r in rows:
    vl[r["vertical"]][r["intended_label"]] += 1
for v in sorted(vl):
    print(f"  {v}: {dict(vl[v])}")

creator_counts = Counter(r["creator"] for r in rows)
dupes = {c: n for c, n in creator_counts.items() if n > 1}
if dupes:
    print(f"\nCreators appearing more than once: {dupes}")
else:
    print(f"\nNo duplicate creators")

vid_counts = Counter(r["video_id"] for r in rows)
vid_dupes = {v: n for v, n in vid_counts.items() if n > 1}
if vid_dupes:
    print(f"\nWARNING: duplicate video_ids: {vid_dupes}")
else:
    print("No duplicate video_ids")

"""Builds backend/fitguide/data/exercises.json.
For every exercise it picks a YouTube tutorial from search candidates (cands.json), then CHECKS the link is
alive and embeddable-info is public using YouTube's oEmbed endpoint. Run it again any time to re-check links:
    python scripts/build_exercises.py --candidates path/to/cands.json
If no candidate passes, the exercise falls back to a YouTube *search* link, which cannot go dead.
We only link to videos (no downloads, no copies), so the video stays on the creator's channel."""
import json, re, sys, pathlib, urllib.request, urllib.parse, concurrent.futures as cf
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from exercises_seed import E

ROOT = pathlib.Path(__file__).resolve().parents[1]
cand_path = sys.argv[sys.argv.index("--candidates") + 1] if "--candidates" in sys.argv else "/tmp/vids/cands.json"
cands = json.load(open(cand_path)) if pathlib.Path(cand_path).exists() else {}
MACHINE = {"machine", "cable", "barbell"}

def oembed(vid):
    url = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(f"https://www.youtube.com/watch?v={vid}")
    try:
        with urllib.request.urlopen(url, timeout=12) as r:
            d = json.load(r)
        return d.get("title"), d.get("author_name")
    except Exception:
        return None

def words(s):
    return {w for w in re.findall(r"[a-z]+", s.lower()) if len(w) > 2 and w not in {"how","the","with","form","proper","exercise","tutorial","perfect","right","way","correct","technique"}}

def pick(ex_id, name):
    nw = words(name)
    scored = []
    for vid, title in cands.get(ex_id, []):
        scored.append((len(nw & words(title)), vid))
    scored.sort(key=lambda x: -x[0])
    for overlap, vid in scored[:4]:
        if overlap == 0:
            continue
        info = oembed(vid)
        if info:
            return vid, info
    return None

with cf.ThreadPoolExecutor(8) as pool:
    picks = dict(zip([e[0] for e in E], pool.map(lambda e: pick(e[0], e[1]), E)))

out, fallback = [], []
for (i, n, m, sec, eq, lvl, pat, cues, mistake, alt) in E:
    p = picks[i]
    if p:
        vid, (title, author) = p
        video = {"url": f"https://www.youtube.com/watch?v={vid}", "title": title, "channel": author, "verified": True}
    else:
        fallback.append(i)
        q = urllib.parse.quote_plus(f"{n} proper form")
        video = {"url": f"https://www.youtube.com/results?search_query={q}", "title": f"Search: {n} proper form", "channel": "YouTube search", "verified": False}
    out.append(dict(id=i, name=n, muscle=m, secondary=sec, equipment=eq, mode="with_machine" if eq in MACHINE else "without_machine",
                    level=lvl, pattern=pat, cues=cues, common_mistake=mistake, alternative=alt, video=video))
(ROOT / "backend/fitguide/data/exercises.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(len(out), "exercises;", len(out) - len(fallback), "verified links;", "fallback to search:", fallback)

"""Build the static manuscript site into dist/.

index.html          one block per week, toggling between its chapter and its ciphers
<week>.html         the assembled chapter (e.g. 2026-W45.html)
entry-<date>.html   one day's scene with its real-world cipher
"""
import os
import re
import glob
import json
import html
from collections import defaultdict
from datetime import date

import markdown

DIST_DIR = "dist"
os.makedirs(DIST_DIR, exist_ok=True)


def week_id(d):
    year, week, _ = d.isocalendar()
    return f"{year}-W{week:02d}"


def week_range(wid):
    year, week = int(wid[:4]), int(wid[6:])
    start = date.fromisocalendar(year, week, 1)
    end = date.fromisocalendar(year, week, 7)
    return f"{start:%b} {start.day} – {end:%b} {end.day}"


def short_date(iso):
    d = date.fromisoformat(iso)
    return f"{d:%b} {d.day}"


def teaser(text, words=9):
    parts = re.sub(r"\s+", " ", text).strip().split(" ")
    return " ".join(parts[:words]).rstrip(",;:.") + ("…" if len(parts) > words else "")


# 1. Load data
events_map = {}
if os.path.exists("data/events_log.json"):
    try:
        with open("data/events_log.json", "r") as f:
            events_map = {e.get("date"): e.get("seed_mapping") for e in json.load(f) if "date" in e}
    except Exception:
        events_map = {}

days_by_week = defaultdict(list)
for path in sorted(glob.glob("fragments/*.json")):
    with open(path, "r", encoding="utf-8") as f:
        frag = json.load(f)
    days_by_week[week_id(date.fromisoformat(frag["date"]))].append(frag)

chapters = {}
for path in glob.glob("chapters/*.md"):
    wid = os.path.basename(path)[:-3]
    with open(path, "r", encoding="utf-8") as f:
        md_text = f.read()
    heading = re.search(r"^#+\s*(.+)$", md_text, re.M)
    title = heading.group(1).strip().strip("*") if heading else "Untitled chapter"
    body = re.sub(r"^#+\s*.+\n", "", md_text, count=1) if heading else md_text
    first_para = next((p for p in body.split("\n\n") if p.strip() and not p.lstrip().startswith(("#", "---", "***"))), "")
    chapters[wid] = {"title": title, "html": markdown.markdown(md_text), "excerpt": teaser(re.sub(r"[*_`>#]", "", first_para), 40)}

# Oldest first, numbered like a book: the first week of the story is Week 1
weeks = sorted(set(days_by_week) | set(chapters))
week_no = {wid: i + 1 for i, wid in enumerate(weeks)}

# 2. Styles: the original typewriter look, plus the week toggle and cipher pages
CSS_STYLES = """
* { box-sizing: border-box; }
body {
    background-color: #ffffff;
    color: #111111;
    font-family: "Courier New", Courier, monospace, serif;
    font-size: 16px;
    line-height: 1.85;
    margin: 0 auto;
    padding: 2.5rem 1.25rem 5rem 1.25rem;
    max-width: 680px;
    word-wrap: break-word;
}
h1, h2, h3 {
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 2rem;
    margin-bottom: 1.5rem;
    border-bottom: 1px solid #111;
    padding-bottom: 0.5rem;
}
p { margin-bottom: 1.5rem; text-indent: 1.5rem; }
p:first-of-type { text-indent: 0; }
hr { border: none; border-top: 1px dashed #ccc; margin: 3rem 0; }
a { color: #111; text-decoration: underline; }
a:hover { background-color: #111; color: #fff; text-decoration: none; }
.meta { color: #777; font-size: 0.8rem; letter-spacing: 0.08em; text-transform: uppercase; }
.nav-bar { margin-bottom: 3rem; font-size: 0.85rem; display: flex; justify-content: space-between; gap: 1rem; }
.week { border-top: 1px solid #111; padding: 1.25rem 0 0.5rem; margin-top: 1.5rem; }
.week-head { display: flex; flex-direction: column; align-items: flex-start; gap: 0.6rem; }
.week-title { font-weight: bold; text-transform: uppercase; letter-spacing: 0.04em; }
.toggle { display: inline-flex; border: 1px solid #111; }
.toggle button {
    font: inherit; font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase;
    background: #fff; color: #111; border: 0; padding: 0.3rem 0.8rem; cursor: pointer;
}
.toggle button + button { border-left: 1px solid #111; }
.toggle button[aria-pressed="true"] { background: #111; color: #fff; }
.panel { margin-top: 1rem; }
.panel[hidden] { display: none; }
.panel p { text-indent: 0; }
.cipher-list { list-style: none; padding: 0; margin: 0; }
.cipher-list a { display: flex; justify-content: space-between; gap: 1rem; padding: 0.55rem 0.25rem; border-bottom: 1px dashed #ccc; text-decoration: none; }
.omen-label { margin-top: 3rem; }
.omen-content {
    margin-top: 0.5rem; padding: 0.75rem 1rem; background-color: #f9f9f9;
    border-left: 2px solid #333; color: #333; font-size: 0.9rem;
}
.pager { display: flex; justify-content: space-between; margin-top: 2.5rem; font-size: 0.85rem; }
.empty { color: #777; }
"""

# Tiny script: switch a week between Chapter and Ciphers. A link to
# index.html#2026-W45-ciphers opens that week on its ciphers.
TOGGLE_JS = """
function show(wid, mode) {
  var w = document.getElementById(wid); if (!w) return;
  w.querySelectorAll('[data-mode]').forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.mode === mode); });
  w.querySelectorAll('.panel').forEach(function (p) { p.hidden = p.dataset.panel !== mode; });
}
document.addEventListener('click', function (e) {
  var b = e.target.closest('[data-mode]'); if (b) show(b.closest('.week').id, b.dataset.mode);
});
function fromHash() {
  var m = location.hash.match(/^#(\\d{4}-W\\d{2})-ciphers$/);
  if (m) { show(m[1], 'ciphers'); document.getElementById(m[1]).scrollIntoView(); }
}
window.addEventListener('hashchange', fromHash); fromHash();
"""


def page(title, body, script=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>{CSS_STYLES}</style>
</head>
<body>
{body}
{f"<script>{script}</script>" if script else ""}
</body>
</html>"""


def write(name, content):
    with open(os.path.join(DIST_DIR, name), "w", encoding="utf-8") as out:
        out.write(content)


# 3. Chapter pages
for wid, ch in chapters.items():
    ciphers_link = f'<p><a href="index.html#{wid}-ciphers">See this week’s ciphers →</a></p>' if days_by_week.get(wid) else ""
    body = f"""<div class="nav-bar"><a href="index.html">← INDEX</a> <span>WEEK {week_no[wid]} · {week_range(wid).upper()}</span></div>
{ch["html"]}
<hr>
{ciphers_link}"""
    write(f"{wid}.html", page(ch["title"], body))

# 4. Cipher (daily entry) pages, with prev/next inside the week
for wid, days in days_by_week.items():
    for i, frag in enumerate(days):
        d = frag["date"]
        prev_link = f'<a href="entry-{days[i-1]["date"]}.html">← CIPHER {i}</a>' if i > 0 else "<span></span>"
        next_link = f'<a href="entry-{days[i+1]["date"]}.html">CIPHER {i + 2} →</a>' if i < len(days) - 1 else "<span></span>"
        body = f"""<div class="nav-bar"><a href="index.html#{wid}-ciphers">← WEEK {week_no[wid]} CIPHERS</a> <span>WEEK {week_no[wid]} · CIPHER {i + 1}</span></div>
<h2>Cipher {i + 1}</h2>
<div class="meta" style="margin-bottom: 1.5rem">Written {date.fromisoformat(d):%A}, {short_date(d)}</div>
{markdown.markdown(frag["text"])}
<div class="meta omen-label">Reality cipher</div>
<div class="omen-content">{html.escape(events_map.get(d) or "Unknown signal")}</div>
<div class="pager">{prev_link}{next_link}</div>"""
        write(f"entry-{d}.html", page(f"Week {week_no[wid]} · Cipher {i + 1}", body))

# 5. Index: one block per week, newest first
blocks = []
for wid in weeks:
    ch, days = chapters.get(wid), days_by_week.get(wid, [])
    start_mode = "chapter" if ch else "ciphers"
    title = ch["title"] if ch else "Chapter in progress"

    if ch:
        chapter_panel = f'<p>{html.escape(ch["excerpt"])}</p><a href="{wid}.html">Read chapter →</a>'
    else:
        chapter_panel = '<p class="empty">This week’s chapter is assembled on Sunday. Until then, read the ciphers.</p>'

    if days:
        items = "".join(
            f'<li><a href="entry-{f["date"]}.html"><span>CIPHER {n}</span><span>→</span></a></li>'
            for n, f in enumerate(days, 1)
        )
        ciphers_panel = f'<ul class="cipher-list">{items}</ul>'
    else:
        ciphers_panel = '<p class="empty">No ciphers recorded for this week.</p>'

    def btn(mode, label):
        return f'<button type="button" data-mode="{mode}" aria-pressed="{str(mode == start_mode).lower()}">{label}</button>'

    blocks.append(f"""<section class="week" id="{wid}">
  <div class="week-head">
    <div><div class="meta">Week {week_no[wid]} · {week_range(wid)}</div><div class="week-title">{html.escape(title)}</div></div>
    <div class="toggle">{btn("chapter", "Chapter")}{btn("ciphers", f"Ciphers ({len(days)})")}</div>
  </div>
  <div class="panel" data-panel="chapter"{"" if start_mode == "chapter" else " hidden"}>{chapter_panel}</div>
  <div class="panel" data-panel="ciphers"{"" if start_mode == "ciphers" else " hidden"}>{ciphers_panel}</div>
</section>""")

index_body = f"""<h1>THE MANUSCRIPT</h1>
<p class="meta">Investigation logs // parallel reception</p>
{"".join(blocks) if blocks else '<p class="empty">No entries recorded yet.</p>'}"""

write("index.html", page("The Manuscript", index_body, TOGGLE_JS))
print(f"Site built in /{DIST_DIR}: {len(weeks)} weeks, {len(chapters)} chapters")

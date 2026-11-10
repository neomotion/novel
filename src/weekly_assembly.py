"""Stitch each finished week's fragments into a chapter.

Every week (Mon-Sun, ISO numbering) that has fragments, has ended by today
(UTC), and has no chapter yet gets assembled, so missed Sundays catch up on
the next run. Set WEEK=2026-W45 to (re)build just that week."""
import os
import glob
import json
from collections import defaultdict
from datetime import date, datetime

from gemini import generate, models_from_env

MODELS = models_from_env("WEEKLY_MODELS", ["gemini-3.1-pro-preview", "gemini-2.5-flash"])


def week_id(d):
    year, week, _ = d.isocalendar()
    return f"{year}-W{week:02d}"


def week_end(wid):
    return date.fromisocalendar(int(wid[:4]), int(wid[6:]), 7)


# 1. Group fragments by week
weeks = defaultdict(list)
for file_path in sorted(glob.glob("fragments/*.json")):
    with open(file_path, "r") as f:
        data = json.load(f)
    weeks[week_id(date.fromisoformat(data["date"]))].append(data)

today = datetime.utcnow().date()
only = os.environ.get("WEEK", "").strip()
if only:
    targets = [only] if only in weeks else []
else:
    targets = [
        w for w in sorted(weeks)
        if week_end(w) <= today and not os.path.exists(f"chapters/{w}.md")
    ]

if not targets:
    print("No weeks to assemble.")
    raise SystemExit(0)

os.makedirs("chapters", exist_ok=True)

# 2. Assemble each week, oldest first
failed = []
for wid in targets:
    raw_text = "\n\n---\n\n".join(f"[{d['date']}]\n{d['text']}" for d in weeks[wid])

    editor_prompt = f"""
You are the continuity editor and prose stylist for a hardboiled, atmospheric mystery novel in the style of Alan Wake.

Below are raw scene fragments written across this week:

{raw_text}

TASK:
1. Seamlessly merge these fragments into a single, cohesive chapter.
2. Fix any POV or tense shifts, smooth transition points between days, and tighten the pacing.
3. DO NOT invent major new plot twists—strictly polish and weld the existing events together.
4. Output the completed chapter in clean Markdown format with a fitting chapter title.
"""

    try:
        chapter_content = generate(MODELS, editor_prompt)
    except Exception as e:
        # Keep going so one bad week doesn't block the rest
        print(f"FAILED {wid}: {e}")
        failed.append(wid)
        continue
    with open(f"chapters/{wid}.md", "w") as f:
        f.write(chapter_content)
    print(f"Assembled chapter {wid}.md from {len(weeks[wid])} fragments")

if failed:
    raise SystemExit(f"Could not assemble: {', '.join(failed)}")

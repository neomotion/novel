"""Turn each finished week's ciphers into the next chapter of one continuous novel.

Each chapter is written with the story so far in hand: a synopsis of every
earlier chapter, the closing passage of the previous chapter, and the open
plot threads. After writing, the chapter's synopsis and the updated threads
are saved to data/story_so_far.json (and the latest threads to data/threads.json)
so the next chapter and the daily job can build on them.

Modes:
  default       assemble every finished week that has no chapter yet, oldest first
  WEEK=2026-W45 rewrite just that week (uses the chapters before it as context)
  REBUILD=1     rewrite every finished week from the beginning, in order
"""
import os
import re
import glob
import json
from collections import defaultdict
from datetime import date, datetime

from google.genai import types
from gemini import generate, models_from_env

MODELS = models_from_env("WEEKLY_MODELS", ["gemini-3.1-pro-preview", "gemini-2.5-flash"])
STORY_FILE = "data/story_so_far.json"
THREADS_FILE = "data/threads.json"


def week_id(d):
    year, week, _ = d.isocalendar()
    return f"{year}-W{week:02d}"


def week_end(wid):
    return date.fromisocalendar(int(wid[:4]), int(wid[6:]), 7)


def load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def chapter_body(wid):
    try:
        with open(f"chapters/{wid}.md", "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""


# 1. Group the ciphers (daily fragments) by week
weeks = defaultdict(list)
for file_path in sorted(glob.glob("fragments/*.json")):
    with open(file_path, "r") as f:
        data = json.load(f)
    weeks[week_id(date.fromisoformat(data["date"]))].append(data)

all_weeks = sorted(weeks)
chapter_no = {w: i + 1 for i, w in enumerate(all_weeks)}  # matches the site's week numbers
today = datetime.utcnow().date()
finished = [w for w in all_weeks if week_end(w) <= today]

story = load_json(STORY_FILE, [])  # one entry per chapter, in order
bible = load_json("data/story_bible.json", {})

only = os.environ.get("WEEK", "").strip()
if os.environ.get("REBUILD", "").strip().lower() in ("1", "true", "yes"):
    targets = finished
    story = []
elif only:
    targets = [only] if only in weeks else []
else:
    targets = [w for w in finished if not os.path.exists(f"chapters/{w}.md")]

if not targets:
    print("No weeks to assemble.")
    raise SystemExit(0)

os.makedirs("chapters", exist_ok=True)

CHAPTER_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "title": types.Schema(type=types.Type.STRING),
        "chapter": types.Schema(type=types.Type.STRING),
        "synopsis": types.Schema(type=types.Type.STRING),
        "threads": types.Schema(
            type=types.Type.OBJECT,
            properties={
                "open_mysteries": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                "characters": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                "clues_and_objects": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                "where_we_left_off": types.Schema(type=types.Type.STRING),
            },
            required=["open_mysteries", "characters", "clues_and_objects", "where_we_left_off"],
        ),
    },
    required=["title", "chapter", "synopsis", "threads"],
)

# 2. Write chapters oldest first; each one needs the one before it
for wid in targets:
    n = chapter_no[wid]
    earlier = [s for s in story if s["week"] < wid]
    threads = earlier[-1].get("threads", {}) if earlier else {}
    prev_ending = ""
    if earlier:
        prev_text = chapter_body(earlier[-1]["week"])
        prev_ending = " ".join(prev_text.split()[-700:])

    synopsis = "\n\n".join(f"Chapter {s['chapter']} — {s['title']}:\n{s['synopsis']}" for s in earlier)
    ciphers = "\n\n---\n\n".join(f"[Cipher {i}, {d['date']}]\n{d['text']}" for i, d in enumerate(weeks[wid], 1))

    if earlier:
        position = f"""This is CHAPTER {n} of an ongoing novel. It must continue directly from Chapter {n - 1}.

THE STORY SO FAR (synopsis of every earlier chapter, in order):
{synopsis}

OPEN THREADS, CHARACTERS, AND CLUES SO FAR:
{json.dumps(threads, indent=2, ensure_ascii=False)}

THE CLOSING PASSAGE OF CHAPTER {n - 1} (pick up from here):
{prev_ending}"""
    else:
        position = "This is CHAPTER 1, the opening of the novel. Establish David, Blackwood Bay, and the first mystery that the whole book will follow."

    prompt = f"""You are the novelist and continuity editor of a serialized psychological horror mystery: a writer-investigator in a
small coastal town, typed pages that come true, a living dark that takes people, and light as the only defense.

STORY BIBLE (premise, world rules, fixed characters, tone, and what to avoid; it overrides any cipher that contradicts it):
{json.dumps(bible, indent=2, ensure_ascii=False)}

{position}

THIS WEEK'S CIPHERS (raw daily scenes, each born from real-world events of that day):
{ciphers}

TASK: Write Chapter {n}.
1. It is one chapter of ONE continuous novel, not a standalone story. Open where the previous chapter ended. Do not
   re-introduce David, the town, or anything the reader already knows, and don't repeat scenes already told; build on
   them. Keep every name, role, place, clue, and established fact consistent with the story so far, even where a
   cipher gets one wrong.
2. Weave this week's ciphers into the ongoing plot, in order. Keep each cipher's key images and events, but you may
   reshape, connect, and bridge them so they read as consequences of what came before, not isolated episodes.
3. Advance the central mystery: pay off or deepen at least one open thread. Each daily cipher is one of the typed
   manuscript pages from the story bible, so show David finding or reckoning with at least one page in the chapter.
   Include at least one night scene of real danger from the dark. Follow every rule in the story bible, especially
   the "avoid" list and the rule against repeating the same uncanny motifs.
4. Hardboiled, restrained, moody, surreal. 1,500 to 2,500 words. End on a hook that pulls into the next chapter.

Return JSON:
- "title": the chapter's title only, without "Chapter" or any number (e.g. "The Thrumming Bay")
- "chapter": the chapter text in Markdown paragraphs, with no title heading
- "synopsis": 150 to 250 words summarizing what happens in this chapter, for continuity in later chapters
- "threads": the story bible after this chapter, kept SHORT so it stays useful as the novel grows:
    - "open_mysteries": at most 8, one sentence each; merge related ones, drop any that are resolved or abandoned
    - "characters": at most 12, each "Name: role and relationship to David" (keep established roles fixed;
      if a cipher contradicts one, follow the established role)
    - "clues_and_objects": at most 12, the ones that still matter, one short phrase each
    - "where_we_left_off": 2 to 3 sentences
"""

    try:
        raw = generate(
            MODELS,
            prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=CHAPTER_SCHEMA),
        )
        result = json.loads(raw)
    except Exception as e:
        # Later chapters depend on this one, so stop here rather than skip ahead
        raise SystemExit(f"Could not assemble {wid} (chapter {n}): {e}")

    title = re.sub(r"^chapter\s+[\w-]+\s*[:.\-–—]\s*", "", result["title"].strip(), flags=re.I) or result["title"].strip()
    with open(f"chapters/{wid}.md", "w") as f:
        f.write(f"# {title}\n\n{result['chapter'].strip()}\n")

    story = [s for s in story if s["week"] != wid]
    story.append({
        "week": wid, "chapter": n, "title": title,
        "synopsis": result["synopsis"].strip(), "threads": result["threads"],
    })
    story.sort(key=lambda s: s["week"])
    save_json(STORY_FILE, story)
    # threads.json always reflects the latest chapter; the daily job reads it
    save_json(THREADS_FILE, story[-1]["threads"])
    print(f"Assembled chapter {n} ({wid}): {title} from {len(weeks[wid])} ciphers")

import os
import glob
import json
import feedparser
import requests
import yfinance as yf
from datetime import datetime
from google.genai import types
from gemini import generate, models_from_env

MODELS = models_from_env("DAILY_MODELS", ["gemini-2.5-flash", "gemini-3.1-pro-preview"])

def fetch_signals():
    signals = []
    
    # Topic 1: Global News (BBC)
    try:
        news_feed = feedparser.parse("https://feeds.bbci.co.uk/news/world/rss.xml")
        if news_feed.entries:
            signals.append(f"Global News: {news_feed.entries[0].title}")
    except Exception:
        pass

    # Topic 2: Technology/Science News (NYT)
    try:
        tech_feed = feedparser.parse("https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml")
        if tech_feed.entries:
            signals.append(f"Tech News: {tech_feed.entries[0].title}")
    except Exception:
        pass

    # Topic 3: Financial Markets (S&P 500 via yfinance)
    try:
        ticker = yf.Ticker("^GSPC")
        hist = ticker.history(period="1d")
        if not hist.empty:
            close_price = hist['Close'].iloc[0]
            signals.append(f"Market (S&P 500): Closed at {close_price:.2f}")
    except Exception:
        pass

    # Topic 4: Nature/Geology (USGS Earthquakes)
    try:
        # Utilizing the USGS standard summary feed for significant recent earthquakes
        url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson"
        response = requests.get(url, timeout=5)
        data = response.json()
        if data.get("features"):
            eq = data["features"][0]["properties"]
            signals.append(f"Geological Event: Magnitude {eq['mag']} earthquake at {eq['place']}")
    except Exception:
        pass

    return signals

signals = fetch_signals()

# 3. Load Context
with open("data/story_bible.json", "r") as f:
    story_bible = json.load(f)

with open("data/threads.json", "r") as f:
    threads = json.load(f)

# The story so far: the latest chapters' synopses, plus the most recent ciphers
# (this week's, or the last few if the week just started) so today follows on.
try:
    with open("data/story_so_far.json", "r") as f:
        story_so_far = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    story_so_far = []
recent_chapters = "\n\n".join(
    f"Chapter {c['chapter']} — {c['title']}: {c['synopsis']}" for c in story_so_far[-2:]
) or "(No chapters yet.)"

recent_files = sorted(glob.glob("fragments/*.json"))[-4:]
recent_ciphers = []
for path in recent_files:
    with open(path, "r") as f:
        frag = json.load(f)
    recent_ciphers.append(f"[{frag['date']}]\n{frag['text']}")
recent_ciphers = "\n\n---\n\n".join(recent_ciphers) or "(None yet.)"

today_str = datetime.utcnow().strftime("%Y-%m-%d")

if os.path.exists(f"fragments/{today_str}.json"):
    print(f"Fragment for {today_str} already exists; nothing to do.")
    raise SystemExit(0)

# 4. Generate Scene with Gemini
prompt = f"""
You are writing one day's page of a serialized psychological horror mystery: a writer-investigator in a small coastal
town, typed pages that come true, a living dark that takes people, and light as the only defense.

STORY BIBLE (premise, world rules, fixed characters, tone, and what to avoid):
{json.dumps(story_bible, indent=2, ensure_ascii=False)}

THE STORY SO FAR (latest chapters):
{recent_chapters}

OPEN THREADS, CHARACTERS, AND CLUES:
{json.dumps(threads, indent=2, ensure_ascii=False)}

THE MOST RECENT DAILY SCENES (today's scene comes right after these):
{recent_ciphers}

REAL-WORLD SEED SIGNALS TODAY:
{json.dumps(signals, indent=2)}

TASK:
1. Review today's real-world signals across News, Tech, Markets, and Nature. Select 1 to 3 of them.
2. Translate the selected signals into eerie weather, radio static, town rumors, or strange omens (NEVER mention the real event explicitly).
3. Write a tight 2-3 paragraph scene that continues directly from the most recent scene. It is one day in a
   continuous novel: keep names, places, and clues consistent, follow up on at least one open thread, and don't
   re-introduce David or the town. Maintain a hardboiled, restrained, moody investigative tone. Follow the story
   bible's tone rules and "avoid" list, and don't reuse the uncanny motif the most recent scene leaned on.
4. Return your response in valid JSON with two fields:
   - "seed_event": (A string describing which real-world events you chose and how you manifested them as omens)
   - "prose": (The 2-3 paragraphs of novel text)
"""

text = generate(
    MODELS,
    prompt,
    config=types.GenerateContentConfig(response_mime_type="application/json"),
)

result = json.loads(text)

# 5. Save outputs
os.makedirs("fragments", exist_ok=True)
fragment_data = {
    "date": today_str,
    "text": result["prose"]
}

with open(f"fragments/{today_str}.json", "w") as f:
    json.dump(fragment_data, f, indent=2)

# Update events cipher log
with open("data/events_log.json", "r") as f:
    events_log = json.load(f)

events_log.append({
    "date": today_str,
    "seed_mapping": result["seed_event"]
})

with open("data/events_log.json", "w") as f:
    json.dump(events_log, f, indent=2)

print(f"Generated fragment for {today_str}")

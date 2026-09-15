import os
import json
from datetime import datetime
import feedparser
from google import genai
from google.genai import types

# 1. Initialize Gemini Client
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# 2. Source Headlines
RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/World.xml",
    "https://feeds.reuters.com/reuters/worldNews"
]

def fetch_signals():
    signals = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:2]:
                signals.append(entry.title)
        except Exception as e:
            print(f"Error fetching feed {feed_url}: {e}")
    return signals[:5]

signals = fetch_signals()

# 3. Load Context
with open("data/story_bible.json", "r") as f:
    story_bible = json.load(f)

with open("data/threads.json", "r") as f:
    threads = json.load(f)

today_str = datetime.utcnow().strftime("%Y-%m-%d")

# 4. Generate Scene with Gemini
prompt = f"""
You are writing a surreal, atmospheric psychological mystery novel inspired by Alan Wake.
Protagonist: {story_bible['protagonist']['name']}, {story_bible['protagonist']['occupation']} in {story_bible['protagonist']['location']}.

WORLD RULES & TONE:
{json.dumps(story_bible['tone_rules'], indent=2)}

ACTIVE PLOT THREADS:
{json.dumps(threads, indent=2)}

REAL-WORLD SEED SIGNALS TODAY:
{signals}

TASK:
1. Select ONE subtle signal/omen inspired by today's real-world events (translate it into eerie weather, radio static, town rumors, or strange omens—NEVER mention the real event explicitly).
2. Write a tight 2-3 paragraph scene fragment continuing the story. Maintain a hardboiled, restrained, moody investigative tone.
3. Return your response in valid JSON with two fields:
   - "seed_event": (The real event and how it was manifested)
   - "prose": (The 2-3 paragraphs of novel text)
"""

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json"
    ),
)

result = json.loads(response.text)

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

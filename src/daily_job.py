import os
import json
import feedparser
import requests
import yfinance as yf
from datetime import datetime
from google import genai
from google.genai import types

# 1. Initialize Gemini Client
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

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
{json.dumps(signals, indent=2)}

TASK:
1. Review today's real-world signals across News, Tech, Markets, and Nature. Select 1 to 3 of them.
2. Translate the selected signals into eerie weather, radio static, town rumors, or strange omens (NEVER mention the real event explicitly).
3. Write a tight 2-3 paragraph scene fragment continuing the story. Maintain a hardboiled, restrained, moody investigative tone.
4. Return your response in valid JSON with two fields:
   - "seed_event": (A string describing which real-world events you chose and how you manifested them as omens)
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

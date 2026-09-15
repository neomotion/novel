import os
import glob
import json
from datetime import datetime
from google import genai
from google.genai import types

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# 1. Gather all weekly fragments
fragment_files = sorted(glob.glob("fragments/*.json"))
if not fragment_files:
    print("No fragments found to assemble.")
    exit(0)

weekly_prose = []
for file_path in fragment_files:
    with open(file_path, "r") as f:
        data = json.load(f)
        weekly_prose.append(f"[{data['date']}]\n{data['text']}")

raw_text = "\n\n---\n\n".join(weekly_prose)

# 2. Prompt Gemini as an Editor
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

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=editor_prompt
)

chapter_content = response.text
week_num = datetime.utcnow().strftime("%Y-W%U")

os.makedirs("chapters", exist_ok=True)
with open(f"chapters/{week_num}.md", "w") as f:
    f.write(chapter_content)

print(f"Assembled and saved chapter {week_num}.md")

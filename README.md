# The Manuscript

An automated, self-writing surreal mystery novel driven by real-world events. Built entirely on GitHub Actions and the Google Gemini API.

## How It Works
1. **The Daily Cipher:** Every day at 3 AM UTC, a GitHub Action triggers a Python script. This script pulls real-world data across four distinct domains:
   - **Global News** (BBC RSS)
   - **Technology & Science** (NYT RSS)
   - **Financial Markets** (S&P 500 via yfinance)
   - **Geological Events** (USGS Earthquake GeoJSON API)
2. **The Manifestation:** The Gemini API receives these signals and acts as an "Alan Wake-style" author, translating real-world events into strange weather, town rumors, and omens. It writes a daily 2-3 paragraph scene fragment.
3. **The Assembly:** Every Sunday, a secondary job acts as the continuity editor, stitching the week's fragments into a polished, cohesive chapter.
4. **The Publication:** A static Python site generator builds a minimalist, typewriter-styled HTML page and deploys it directly to GitHub Pages.

## Viewing the Story
The live manuscript can be read here: [https://neomotion.github.io/novel/](https://neomotion.github.io/novel/)

*Tap the "?? CIPHER" toggle beneath any entry to reveal the hidden real-world events that spawned that specific scene.*

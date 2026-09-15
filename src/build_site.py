import os
import glob
import json
import markdown

DIST_DIR = "dist"
os.makedirs(DIST_DIR, exist_ok=True)

# 1. Load real-world event mappings
events_map = {}
if os.path.exists("data/events_log.json"):
    try:
        with open("data/events_log.json", "r") as f:
            events_data = json.load(f)
            events_map = {item.get("date"): item.get("seed_mapping") for item in events_data if "date" in item}
    except Exception:
        events_map = {}

# 2. Minimalist Manuscript CSS
CSS_STYLES = """
* { box-sizing: border-box; }
body {
    background-color: #ffffff;
    color: #111111;
    font-family: "Courier New", Courier, monospace, serif;
    font-size: 16px;
    line-height: 1.85;
    margin: 0;
    padding: 2.5rem 1.25rem 5rem 1.25rem;
    max-width: 680px;
    margin-left: auto;
    margin-right: auto;
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
p {
    margin-bottom: 1.5rem;
    text-indent: 1.5rem;
}
p:first-of-type {
    text-indent: 0;
}
hr {
    border: none;
    border-top: 1px dashed #ccc;
    margin: 3rem 0;
}
a {
    color: #111;
    text-decoration: underline;
}
a:hover {
    background-color: #111;
    color: #fff;
    text-decoration: none;
}
.omen-section {
    margin-top: 3.5rem;
    padding-top: 1rem;
    border-top: 1px solid #eaeaea;
    font-size: 0.85rem;
    color: #777;
}
details summary {
    cursor: pointer;
    user-select: none;
    outline: none;
    font-size: 0.8rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #999;
}
details summary:hover {
    color: #111;
}
.omen-content {
    margin-top: 0.75rem;
    padding: 0.75rem 1rem;
    background-color: #f9f9f9;
    border-left: 2px solid #333;
    color: #333;
}
.nav-bar {
    margin-bottom: 3rem;
    font-size: 0.85rem;
    display: flex;
    justify-content: space-between;
}
"""

def generate_html_page(title, body_content, omens_list=None, back_link=False):
    nav = f'<div class="nav-bar"><a href="index.html">← INDEX</a> <span>MANUSCRIPT ARCHIVE</span></div>' if back_link else ''
    
    omen_html = ""
    if omens_list:
        items = "".join([f"<li><strong>{date}:</strong> {desc}</li>" for date, desc in omens_list])
        omen_html = f"""
        <div class="omen-section">
            <details>
                <summary>?? REVEAL REALITY CIPHER</summary>
                <div class="omen-content">
                    <ul style="padding-left: 1.2rem; margin: 0;">{items}</ul>
                </div>
            </details>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>{CSS_STYLES}</style>
</head>
<body>
    {nav}
    {body_content}
    {omen_html}
</body>
</html>"""

# 3. Build Chapter Pages
chapter_files = sorted(glob.glob("chapters/*.md"), reverse=True)
chapter_links = []

for filepath in chapter_files:
    filename = os.path.basename(filepath)
    slug = filename.replace(".md", "")
    with open(filepath, "r", encoding="utf-8") as f:
        md_text = f.read()
    
    html_body = markdown.markdown(md_text)
    
    # Collect matching omens
    relevant_omens = [(d, m) for d, m in events_map.items()]
    
    page_html = generate_html_page(title=slug, body_content=html_body, omens_list=relevant_omens, back_link=True)
    with open(os.path.join(DIST_DIR, f"{slug}.html"), "w", encoding="utf-8") as out:
        out.write(page_html)
    
    chapter_links.append(f'<li><a href="{slug}.html">{slug.upper()}</a></li>')

# 4. Build Latest Daily Fragments Section
fragment_files = sorted(glob.glob("fragments/*.json"), reverse=True)
fragment_entries = []

for filepath in fragment_files[:6]: # Show current week unedited fragments
    with open(filepath, "r", encoding="utf-8") as f:
        frag_data = json.load(f)
    f_date = frag_data.get("date", "")
    f_text = frag_data.get("text", "")
    f_omen = events_map.get(f_date, "Unknown signal")
    
    fragment_entries.append(f"""
    <div style="margin-bottom: 2rem;">
        <h3 style="font-size: 0.95rem; margin-bottom: 0.5rem;">ENTRY: {f_date}</h3>
        <p>{f_text}</p>
        <details>
            <summary>?? CIPHER</summary>
            <div class="omen-content">{f_omen}</div>
        </details>
    </div>
    """)

# 5. Build Home Index (`index.html`)
index_body = f"""
<h1>THE MANUSCRIPT</h1>
<p style="color: #666; font-size: 0.85rem;">INVESTIGATION LOGS // PARALLEL RECEPTION</p>

<h2>CURRENT WEEK (UNASSEMBLED FRAGMENTS)</h2>
{"".join(fragment_entries) if fragment_entries else "<p>No active fragments recorded yet this week.</p>"}

<h2>ASSEMBLED CHAPTERS</h2>
{"<ul>" + "".join(chapter_links) + "</ul>" if chapter_links else "<p>No chapters assembled yet.</p>"}
"""

index_html = generate_html_page("The Manuscript", index_body, back_link=False)
with open(os.path.join(DIST_DIR, "index.html"), "w", encoding="utf-8") as out:
    out.write(index_html)

print("Site built successfully in /dist")

#!/usr/bin/env python3
"""Rebuild the original advertising case studies as editorial portfolio pages.
Uses only material in the source archive and editorial.json. Never rewrites media files.
"""
from pathlib import Path
from html import escape
import json
import re

root = Path("portfolio-assets/danifpradana-portfolio")
manifest = json.loads(Path("portfolio-assets/manifest.json").read_text(encoding="utf-8"))
data = json.loads((root / "assets/editorial.json").read_text(encoding="utf-8"))
cases = data["case_studies"]
backup = root / "original-pages"
backup.mkdir(parents=True, exist_ok=True)
source_groups = {p["slug"]: p for p in manifest["projects"]}
media_pattern = re.compile(r"<video\b[\s\S]*?</video>|<img\b[^>]*>", re.IGNORECASE)
files_written = []

def esc(s):
    return escape(str(s), quote=True)

def stylize(title):
    words = title.split()
    cut = max(1, (len(words) + 1) // 2)
    return esc(" ".join(words[:cut])) + " <em>" + esc(" ".join(words[cut:])) + "</em>" if len(words) >= 3 else esc(title)

def build(project, index):
    slug = project["slug"]
    original = root / "projects" / slug / "index.html"
    old = backup / (slug + ".html")
    if not old.exists():
        if not original.is_file():
            raise ValueError("Missing original case study: " + slug)
        old.write_bytes(original.read_bytes())
    source = old.read_text(encoding="utf-8")
    media = media_pattern.findall(source)
    if not media:
        raise ValueError("Original case study has no media: " + slug)
    group = source_groups[slug]
    assets = group["assets"]
    cover = next((x["name"] for x in assets if re.match(r"cover\.(?:jpg|jpeg|png|webp)$", x["name"], re.I)), None)

    gallery = []
    for n, tag in enumerate(media, 1):
        is_video = tag.lower().startswith("<video")
        tag = re.sub(r'\s+preload="[^"]*"', "", tag, flags=re.I)
        tag = re.sub(r'\s+loading="[^"]*"', "", tag, flags=re.I)
        tag = re.sub(r'\s+decoding="[^"]*"', "", tag, flags=re.I)
        if is_video:
            tag = re.sub(r"<video\b", '<video preload="none"', tag, count=1, flags=re.I)
        else:
            tag = re.sub(r"<img\b", '<img loading="lazy" decoding="async"', tag, count=1, flags=re.I)
        label = ("Film " if is_video else "Visual ") + str(n).zfill(2)
        gallery.append(f'<figure class="media-card { "video" if is_video else "image"}">{tag}<figcaption>{esc(label)}</figcaption></figure>')

    chapters = []
    for n, (headline, paragraph) in enumerate(project["parts"], 1):
        chapters.append(f'<section class="chapter"><span class="chapter-no">{n:02d} / The thinking</span><h2>{esc(headline)}</h2><p>{paragraph}</p></section>')

    credits = [["My contribution", project["role"]]]
    for role, name in project.get("credits", []):
        if role == "Copywriter" and "copywriting" in project["role"].lower():
            continue
        credits.append([role, name])
    credit_html = "".join(f'<div class="credit-row"><strong>{esc(label)}</strong><span>{esc(person)}</span></div>' for label, person in credits)

    facts = [
        ["Client", project["client"]],
        ["Discipline", project["kind"]],
        ["My contribution", project["role"]]
    ]
    facts_html = "".join(f'<div><span class="fact-label">{esc(key)}</span><span class="fact-value">{esc(value)}</span></div>' for key, value in facts)

    prior = cases[(index - 1) % len(cases)]
    following = cases[(index + 1) % len(cases)]
    cover_html = f'<figure class="case-cover"><img src="{esc(cover)}" alt="{esc(project["title"])} campaign cover" fetchpriority="high"></figure>' if cover else f'<figure class="case-cover no-cover">{esc(project["title"])}</figure>'
    doc = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#f1efe8">
<meta name="description" content="{esc(project["deck"])}">
<meta property="og:title" content="{esc(project["title"])} | Dan Pradana">
<meta property="og:description" content="{esc(project["deck"])}">
<title>{esc(project["title"])} | Dan Pradana</title>
<link rel="stylesheet" href="../../assets/case-study.css">
</head>
<body>
<a class="skip" href="#story">Skip to story</a>
<header class="topbar"><div class="shell topbar-inner"><a class="brand" href="../../../../index.html">dan pradana<b>.</b></a><a class="back-link" href="../../../../index.html#advertising">All advertising work ↗</a></div></header>
<main id="story">
<section class="case-intro shell">
<div class="topline"><span class="eyebrow">Advertising / Case study {index+1:02d}</span><span class="eyebrow">{esc(project["client"])}</span></div>
<h1>{stylize(project["title"])}</h1>
<div class="deck-grid"><p class="hook">{esc(project["hook"])}</p><p class="summary">{esc(project["deck"])}</p></div>
</section>
{cover_html}
<div class="shell"><div class="case-facts">{facts_html}</div></div>
<section class="thinking shell" aria-label="Creative thinking"><div class="rail">Behind the idea / {index+1:02d}</div><div>{''.join(chapters)}</div></section>
<section class="gallery"><div class="shell"><div class="gallery-lead"><div><span class="eyebrow">Selected executions</span><h2>See the <em>work.</em></h2></div><p>Original campaign imagery and films from Dan Pradana's archive, hosted in this repository.</p></div><div class="media-grid">{''.join(gallery)}</div></div></section>
<section class="credits shell"><div class="credits-grid"><div><span class="eyebrow">The people behind it</span><h2>Creative <em>credits.</em></h2></div><div class="credits-table">{credit_html}</div></div></section>
<nav class="next-nav" aria-label="Other case studies"><div class="shell nav-grid">
<a class="nav-item previous" href="../{esc(prior["slug"])}/index.html"><span>← Previous project</span><strong>{esc(prior["title"])}</strong></a>
<a class="nav-item next" href="../{esc(following["slug"])}/index.html"><span>Next project ↗</span><strong>{esc(following["title"])}</strong></a>
</div></nav>
</main>
<footer class="site-footer"><div class="shell site-footer-inner"><a class="brand" href="../../../../index.html">dan pradana<b>.</b></a><span>Words, ideas &amp; worlds.</span></div></footer>
</body></html>'''
    if "—" in doc:
        raise ValueError("Em dash found in generated case study: " + slug)
    original.write_text(doc, encoding="utf-8")
    files_written.append(str(original))
    print(f"{index+1:02d}. {project['title']} ({len(media)} original media elements)")

for index, item in enumerate(cases):
    build(item, index)
assert len(files_written) == 14
print(f"Rendered {len(files_written)} case studies and preserved source copies in {backup}")

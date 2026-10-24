#!/usr/bin/env python3
"""Import every safe file from a portfolio ZIP and build a browser-friendly manifest.
Runs on GitHub Actions, not on the visitor's browser.
"""
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import quote

source_dir = Path(sys.argv[1])
destination = Path("portfolio-assets")
archives = sorted(source_dir.glob("*.zip"))
if not archives:
    raise SystemExit("ERROR: No ZIP attached to the release.")
if len(archives) > 1:
    raise SystemExit("ERROR: More than one ZIP found; attach only the original portfolio ZIP.")

destination.mkdir(exist_ok=True)
archive = archives[0]
total = 0
seen = set()
with zipfile.ZipFile(archive) as z:
    for info in z.infolist():
        parts = PurePosixPath(info.filename).parts
        if not parts or info.is_dir() or "__MACOSX" in parts or info.filename.endswith(".DS_Store"):
            continue
        if any(part in ("", ".", "..") for part in parts) or info.filename.startswith("/") or "\\" in info.filename:
            raise SystemExit("ERROR: unsafe ZIP entry: " + info.filename)
        # Reject symbolic links. Only ordinary files are copied.
        if ((info.external_attr >> 16) & 0o170000) == 0o120000:
            raise SystemExit("ERROR: symlink in ZIP: " + info.filename)
        normalized = "/".join(parts)
        if normalized in seen:
            raise SystemExit("ERROR: duplicate ZIP entry: " + normalized)
        seen.add(normalized)
        out = destination.joinpath(*parts)
        out.parent.mkdir(parents=True, exist_ok=True)
        with z.open(info) as source, out.open("wb") as target:
            shutil.copyfileobj(source, target, length=1024 * 1024)
        total += 1

image_ext = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif", ".svg"}
video_ext = {".mp4", ".webm", ".m4v", ".mov"}
files = [p for p in destination.rglob("*") if p.is_file() and p.name != "manifest.json"]
# Optional single root folder is preserved in the repository but ignored for display grouping.
parts_list = [p.relative_to(destination).parts for p in files]
wrapper = parts_list[0][0] if parts_list else None
if not all(len(parts) > 1 and parts[0] == wrapper for parts in parts_list):
    wrapper = None

def nice(s):
    import re
    return re.sub(r"[_-]+", " ", s).strip() or "Other work"

groups = {}
for p in sorted(files, key=lambda x: str(x).lower()):
    rel = p.relative_to(destination)
    display_parts = rel.parts[1:] if wrapper else rel.parts
    project = display_parts[0] if len(display_parts) > 1 else "Other Work"
    if project.lower() in ("assets", "img", "images", "media", "files", "portfolio", "projects") and len(display_parts) > 2:
        project = display_parts[1]
    ext = p.suffix.lower()
    kind = "image" if ext in image_ext else "video" if ext in video_ext else "file"
    entry = {
        "name": p.name,
        "path": rel.as_posix(),
        "url": "portfolio-assets/" + "/".join(quote(part, safe="") for part in rel.parts),
        "type": kind,
        "bytes": p.stat().st_size,
    }
    groups.setdefault(project, []).append(entry)

result = {
    "source_archive": archive.name,
    "file_count": len(files),
    "projects": [
        {
            "name": nice(name),
            "slug": name,
            "file_count": len(items),
            "assets": sorted(items, key=lambda a: ({"image": 0, "video": 1, "file": 2}[a["type"]], a["name"].lower()))
        } for name, items in sorted(groups.items(), key=lambda kv: kv[0].lower())
    ],
}
(destination / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"IMPORTED {total} files from {archive.name} across {len(groups)} portfolio folders")
print(f"Total extracted bytes: {sum(p.stat().st_size for p in files):,}")

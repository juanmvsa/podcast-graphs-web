#!/usr/bin/env python3
"""
build script to prepare the static site for deployment to cloudflare pages.
copies graph HTML files and required lib dependencies to the site directory.
"""

import json
import shutil
from pathlib import Path

# define paths.
PROJECT_ROOT = Path(__file__).parent.parent
GRAPHS_DIR = PROJECT_ROOT / "graphs"
LIB_DIR = PROJECT_ROOT / "lib"
INDEX_HTML = PROJECT_ROOT / "index.html"
STYLES_CSS = PROJECT_ROOT / "styles.css"
PIPELINE_DOC = PROJECT_ROOT / "docs" / "pipeline.html"
SITE_DIR = PROJECT_ROOT / "site"
SITE_GRAPHS_DIR = SITE_DIR / "graphs"

# Cloudflare Pages file size limit.
MAX_FILE_SIZE_MB = 25
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def copy_graphs():
    """Sync graphs/ to site/graphs/, replacing stale content.

    Files exceeding Cloudflare's 25 MB limit are automatically excluded.
    """
    print(f"\nsyncing graphs from {GRAPHS_DIR} to {SITE_GRAPHS_DIR}")

    if not GRAPHS_DIR.exists():
        print(f"error: {GRAPHS_DIR} does not exist")
        return

    # Remove old site/graphs to avoid stale shows from previous runs.
    if SITE_GRAPHS_DIR.exists():
        shutil.rmtree(SITE_GRAPHS_DIR)

    skipped = []

    def _ignore_oversized(directory, contents):
        """shutil.copytree ignore callback: skip files over the size limit."""
        ignored = []
        for name in contents:
            path = Path(directory) / name
            if path.is_file() and path.stat().st_size > MAX_FILE_SIZE_BYTES:
                size_mb = path.stat().st_size / (1024 * 1024)
                skipped.append((path.relative_to(GRAPHS_DIR), size_mb))
                ignored.append(name)
        return ignored

    shutil.copytree(GRAPHS_DIR, SITE_GRAPHS_DIR, ignore=_ignore_oversized)

    if skipped:
        print(f"⚠️  skipped {len(skipped)} file(s) exceeding {MAX_FILE_SIZE_MB} MB:")
        for rel_path, size_mb in skipped:
            print(f"    {rel_path} ({size_mb:.1f} MB)")
    print("✓ graphs synced successfully")


def copy_lib():
    """copy lib directory to site/lib/ for JavaScript dependencies."""
    print(f"\ncopying lib from {LIB_DIR} to {SITE_DIR / 'lib'}")

    if not LIB_DIR.exists():
        print(f"error: {LIB_DIR} does not exist")
        return

    dest_lib = SITE_DIR / "lib"
    shutil.copytree(LIB_DIR, dest_lib, dirs_exist_ok=True)
    print("✓ lib copied successfully")

def copy_index():
    """copy index.html to site/ root."""
    print(f"\ncopying index.html from {INDEX_HTML} to {SITE_DIR}")

    if not INDEX_HTML.exists():
        print(f"error: {INDEX_HTML} does not exist")
        return

    dest_index = SITE_DIR / "index.html"
    shutil.copy2(INDEX_HTML, dest_index)
    print("✓ index.html copied successfully")

def copy_styles():
    """copy styles.css to site/ root."""
    print(f"\ncopying styles.css from {STYLES_CSS} to {SITE_DIR}")

    if not STYLES_CSS.exists():
        print(f"error: {STYLES_CSS} does not exist")
        return

    shutil.copy2(STYLES_CSS, SITE_DIR / "styles.css")
    print("✓ styles.css copied successfully")

def copy_pipeline_doc():
    """copy the pipeline reference doc to site/pipeline.html (served at /pipeline.html)."""
    print(f"\ncopying pipeline doc from {PIPELINE_DOC} to {SITE_DIR}")

    if not PIPELINE_DOC.exists():
        print(f"error: {PIPELINE_DOC} does not exist")
        return

    shutil.copy2(PIPELINE_DOC, SITE_DIR / "pipeline.html")
    print("✓ pipeline.html copied successfully")


def build_slim_topics():
    """Create a slim topics.json for the frontend, stripping large fields."""
    src = GRAPHS_DIR / "topics.json"
    dest = SITE_GRAPHS_DIR / "topics.json"

    if not src.exists():
        print("\n⚠️  graphs/topics.json not found — topic browsing will be disabled")
        return

    print("\nbuilding slim topics.json for frontend...")
    with open(src) as f:
        data = json.load(f)

    # Keep only fields the frontend uses
    slim_topics = []
    for t in data.get("topics", []):
        slim_topics.append({
            "topic_id": t["topic_id"],
            "topic_words": t.get("topic_words", []),
            "topic_label": t.get("topic_label", ""),
            "episode_count": t.get("episode_count", 0),
            "episodes": t.get("episodes", []),
        })

    slim = {
        "topics": slim_topics,
        "episode_topics": data.get("episode_topics", {}),
    }

    with open(dest, "w") as f:
        json.dump(slim, f, separators=(",", ":"))

    size_mb = dest.stat().st_size / (1024 * 1024)
    print(f"✓ topics.json built ({size_mb:.1f} MB, stripped from {src.stat().st_size / 1024 / 1024:.1f} MB)")


def generate_stats():
    """generate statistics about the built site."""
    print("\n" + "="*60)
    print("build statistics")
    print("="*60)

    # count HTML files.
    html_files = list(SITE_GRAPHS_DIR.rglob("*.html"))
    print(f"total HTML files: {len(html_files)}")

    # count by podcast.
    podcasts = {}
    for html_file in html_files:
        podcast = html_file.parent.name
        podcasts[podcast] = podcasts.get(podcast, 0) + 1

    for podcast, count in sorted(podcasts.items()):
        print(f"  {podcast}: {count} files")

    # calculate total size.
    total_size = sum(f.stat().st_size for f in SITE_DIR.rglob("*") if f.is_file())
    print(f"\ntotal site size: {total_size / 1024 / 1024:.2f} MB")
    print("="*60)

def main():
    """main build process."""
    print("building static site for cloudflare pages deployment")
    print(f"project root: {PROJECT_ROOT}")
    print(f"site directory: {SITE_DIR}")

    # ensure site directory exists.
    SITE_DIR.mkdir(exist_ok=True)

    # copy files.
    copy_graphs()
    copy_lib()
    copy_index()
    copy_styles()
    copy_pipeline_doc()
    build_slim_topics()

    # generate stats.
    generate_stats()

    print("\n✓ build complete! site/ directory is ready for deployment.")
    print("\nnext steps:")
    print("  ./scripts/deploy.sh")
    print("  or: npx wrangler pages deploy site --project-name=podcast-graphs-web")

if __name__ == "__main__":
    main()

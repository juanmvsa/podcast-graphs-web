#!/usr/bin/env python3
"""
build script to prepare the static site for deployment to cloudflare pages.
copies graph HTML files and required lib dependencies to the site directory.
"""

import shutil
from pathlib import Path

# define paths.
PROJECT_ROOT = Path(__file__).parent.parent
GRAPHS_DIR = PROJECT_ROOT / "graphs"
LIB_DIR = PROJECT_ROOT / "lib"
INDEX_HTML = PROJECT_ROOT / "index.html"
SITE_DIR = PROJECT_ROOT / "site"
SITE_GRAPHS_DIR = SITE_DIR / "graphs"


def copy_lib():
    """copy lib directory to site/lib/ for JavaScript dependencies."""
    print(f"\ncopying lib from {LIB_DIR} to {SITE_DIR / 'lib'}")

    if not LIB_DIR.exists():
        print(f"error: {LIB_DIR} does not exist")
        return

    dest_lib = SITE_DIR / "lib"
    shutil.copytree(LIB_DIR, dest_lib, dirs_exist_ok=True)
    print(f"✓ lib copied successfully")

def copy_index():
    """copy index.html to site/ root."""
    print(f"\ncopying index.html from {INDEX_HTML} to {SITE_DIR}")

    if not INDEX_HTML.exists():
        print(f"error: {INDEX_HTML} does not exist")
        return

    dest_index = SITE_DIR / "index.html"
    shutil.copy2(INDEX_HTML, dest_index)
    print(f"✓ index.html copied successfully")

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

    # note: graphs are already in place, no need to copy them.
    # only copy lib and index.html.

    # copy files.
    copy_lib()
    copy_index()

    # generate stats.
    generate_stats()

    print("\n✓ build complete! site/ directory is ready for deployment.")
    print("\nnext steps:")
    print("1. cd site/")
    print("2. git init (if not already a git repo)")
    print("3. git add .")
    print("4. git commit -m 'initial site build'")
    print("5. push to github and connect to cloudflare pages")
    print("   or use: npx wrangler pages deploy . --project-name=podcast-graphs")

if __name__ == "__main__":
    main()

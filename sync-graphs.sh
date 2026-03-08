#!/bin/bash
# sync-graphs.sh
# automatically sync graphs from analysis project to web project

set -e  # exit on error

SOURCE="/Volumes/juan_mac_mini_ssd/podcast-conversations/outputs/graphs"
DEST="/Volumes/juan_mac_mini_ssd/podcast-graphs-web/graphs"

echo "==================================="
echo "podcast graphs sync utility"
echo "==================================="
echo ""

# check source exists
if [ ! -d "$SOURCE" ]; then
    echo "error: source directory not found: $SOURCE"
    exit 1
fi

# create dest if needed
mkdir -p "$DEST"

echo "syncing graphs..."
echo "source: $SOURCE"
echo "dest: $DEST"
echo ""

# sync with rsync
# -a: archive mode (preserves permissions, times, etc)
# -v: verbose
# --delete: remove files in dest that don't exist in source
rsync -av --delete "$SOURCE/" "$DEST/"

echo ""
echo "✓ graphs synced successfully!"
echo ""

# count files
html_count=$(find "$DEST" -name "*.html" | wc -l | tr -d ' ')
echo "total HTML files: $html_count"
echo ""

# ask to commit
read -p "commit and push changes? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd /Volumes/juan_mac_mini_ssd/podcast-graphs-web

    git add graphs/
    git status
    echo ""

    read -p "enter commit message (or press enter for default): " commit_msg

    if [ -z "$commit_msg" ]; then
        commit_msg="sync: update graphs ($(date +%Y-%m-%d))"
    fi

    git commit -m "$commit_msg"
    git push

    echo ""
    echo "✓ changes committed and pushed!"
    echo "cloudflare pages will auto-deploy in ~2 minutes"
else
    echo "skipping git commit"
fi

echo ""
echo "done!"

#!/bin/bash
# Build, validate, and deploy the static site to Cloudflare Pages.
#
# This script ensures a clean deployment by:
#   1. Clearing caches so no stale artifacts leak through
#   2. Rebuilding site/ from scratch (syncs graphs/, lib/, index.html)
#      Files exceeding Cloudflare's 25 MB limit are automatically excluded
#   3. Removing .json and .csv data files from site/graphs/ (the frontend
#      only needs .html visualizations; keeps site under 20K file limit)
#   4. Regenerating index.json inside site/ from the synced graphs
#   5. Validating all files are under Cloudflare's 25 MB limit
#   6. Deploying site/ to Cloudflare Pages
#
# Usage: ./scripts/deploy.sh [extra wrangler flags]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "================================================"
echo "🧹 CLEAN DEPLOYMENT"
echo "================================================"
echo ""

# 1. Clear caches
echo "🗑️  Clearing caches..."
rm -rf .wrangler/
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo "✓ Caches cleared"
echo ""

# 2. Build site/ from scratch (wipes old site/graphs, copies fresh data)
echo "🔨 Building site/..."
uv run scripts/build_site.py
echo ""

# 3. Strip .json and .csv data files from graphs/ (frontend only needs .html)
# Cloudflare Pages free tier allows max 20,000 files per deployment.
# Preserve topics.json which is needed by the frontend for topic browsing.
echo "✂️  Removing .json and .csv data files from site/graphs/..."
find site/graphs -type f \( -name "*.json" -o -name "*.csv" \) ! -name "topics.json" -delete
remaining=$(find site/ -type f | wc -l | tr -d ' ')
echo "✓ Data files removed ($remaining files remain — 20,000 limit)"
echo ""

# 4. Regenerate index.json inside site/ from the freshly-synced graphs
echo "🔄 Generating site/index.json..."
uv run scripts/generate_index.py --graphs-dir site/graphs --output site/index.json
echo ""

# 5. Validate file sizes
echo "🔍 Validating deployment files..."
uv run scripts/validate_deployment.py
echo ""

# 6. Deploy
echo "🚀 Deploying to Cloudflare Pages..."
npx wrangler pages deploy site --project-name=podcast-graphs-web "$@"

echo ""
echo "================================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "================================================"

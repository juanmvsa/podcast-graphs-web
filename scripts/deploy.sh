#!/bin/bash
# Build, validate, and deploy the static site to Cloudflare Pages.
#
# This script ensures a clean deployment by:
#   1. Clearing caches so no stale artifacts leak through
#   2. Rebuilding site/ from scratch (syncs graphs/, lib/, index.html)
#   3. Regenerating index.json inside site/ from the freshly-copied graphs
#   4. Validating all files are under Cloudflare's 25 MB limit
#   5. Deploying site/ to Cloudflare Pages
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

# 3. Regenerate index.json inside site/ from the freshly-synced graphs
echo "🔄 Generating site/index.json..."
uv run scripts/generate_index.py --graphs-dir site/graphs --output site/index.json
echo ""

# 4. Validate file sizes
echo "🔍 Validating deployment files..."
uv run scripts/validate_deployment.py
echo ""

# 5. Deploy
echo "🚀 Deploying to Cloudflare Pages..."
npx wrangler pages deploy site --project-name=podcast-graphs-web "$@"

echo ""
echo "================================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "================================================"

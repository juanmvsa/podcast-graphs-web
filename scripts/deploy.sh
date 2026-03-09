#!/bin/bash
# Safe deployment wrapper that clears caches and validates before deploying

set -e  # Exit on error

echo "================================================"
echo "🧹 CLEAN DEPLOYMENT - Starting fresh"
echo "================================================"
echo ""

# 1. Clear Wrangler cache
echo "🗑️  Clearing Wrangler cache..."
rm -rf .wrangler/
echo "✓ Wrangler cache cleared"
echo ""

# 2. Clear any Python cache
echo "🗑️  Clearing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo "✓ Python cache cleared"
echo ""

# 3. Regenerate index.json from scratch
echo "🔄 Regenerating index.json from site/graphs..."
cd site
uv run python3 -c "
import sys
sys.path.insert(0, '../scripts')
from pathlib import Path
from generate_index import scan_graphs_directory
import json

graphs_dir = Path('graphs')
output_file = Path('index.json')

# Remove old index if exists
if output_file.exists():
    output_file.unlink()

print(f'Scanning: {graphs_dir.absolute()}')
index_data = scan_graphs_directory(graphs_dir)

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(index_data, f, indent=2, ensure_ascii=False)

print(f'✓ Generated fresh index.json')
print(f'  Shows: {index_data[\"totalShows\"]}')
print(f'  Episodes: {index_data[\"totalEpisodes\"]}')
"
cd ..
echo ""

# 4. Validate deployment files
echo "🔍 Validating deployment files..."
uv run scripts/validate_deployment.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Deployment aborted due to validation errors"
    exit 1
fi
echo ""

# 5. Deploy to Cloudflare Pages
echo "🚀 Deploying to Cloudflare Pages..."
npx wrangler pages deploy site --project-name=podcast-graphs-web "$@"

echo ""
echo "================================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "================================================"

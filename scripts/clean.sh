#!/bin/bash
# Clean all caches and temporary files

set -e

echo "🧹 Cleaning repository caches..."
echo ""

# Clear Wrangler cache
if [ -d ".wrangler" ]; then
    echo "  Removing .wrangler/"
    rm -rf .wrangler/
fi

# Clear Python caches
echo "  Removing Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Clear temporary files
echo "  Removing temporary files..."
find . -type f -name "*.tmp" -delete 2>/dev/null || true
find . -type f -name "*.bak" -delete 2>/dev/null || true

# Clear old index files (will be regenerated)
if [ -f "site/index.json" ]; then
    echo "  Removing old site/index.json (will be regenerated)"
    rm -f site/index.json
fi

echo ""
echo "✅ Repository cleaned!"
echo ""
echo "Next steps:"
echo "  1. Regenerate index: cd site && uv run python3 -c '...'"
echo "  2. Deploy: ./scripts/deploy.sh"

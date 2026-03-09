#!/bin/bash
# Safe deployment wrapper that validates file sizes before deploying

set -e  # Exit on error

echo "🔍 Validating deployment files..."
uv run scripts/validate_deployment.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Deployment aborted due to validation errors"
    exit 1
fi

echo ""
echo "🚀 Deploying to Cloudflare Pages..."
npx wrangler pages deploy site --project-name=podcast-graphs-web "$@"

echo ""
echo "✅ Deployment complete!"

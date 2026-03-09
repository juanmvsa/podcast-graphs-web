# Deployment Guide

This project is deployed to Cloudflare Pages, which has a **25MB file size limit**.

## Safeguards Against Large Files

Multiple layers of protection prevent large files from being deployed:

### 1. Git Pre-Commit Hook (`.git/hooks/pre-commit`)
Automatically checks file sizes before allowing commits. Prevents files >25MB from being committed.

**Triggers on:** `git commit`

**To bypass** (not recommended): `git commit --no-verify`

### 2. Validation Script (`scripts/validate_deployment.py`)
Scans the `site/` directory for files exceeding 25MB.

**Usage:**
```bash
uv run scripts/validate_deployment.py
```

### 3. Safe Deployment Script (`scripts/deploy.sh`)
Wrapper around wrangler that validates before deploying.

**Usage:**
```bash
./scripts/deploy.sh
```

This is the **recommended way to deploy**. It runs validation automatically.

### 4. Cloudflare Ignore File (`.cfignore`)
Excludes specific paths from deployment. Currently excludes:
- Development files (`.venv/`, `scripts/`, etc.)
- Oversized summary graphs

## Deployment Workflow

### Recommended Process

1. **Generate graphs** (if needed):
   ```bash
   uv run scripts/generate_entity_graphs.py
   ```

2. **Generate index** for site directory:
   ```bash
   cd site
   uv run python3 -c "
   import sys; sys.path.insert(0, '../scripts')
   from pathlib import Path
   from generate_index import scan_graphs_directory
   import json
   data = scan_graphs_directory(Path('graphs'))
   with open('index.json', 'w') as f:
       json.dump(data, f, indent=2)
   print(f'Generated index with {data[\"totalShows\"]} shows')
   "
   cd ..
   ```

3. **Validate** before deploying:
   ```bash
   uv run scripts/validate_deployment.py
   ```

4. **Deploy** using the safe wrapper:
   ```bash
   ./scripts/deploy.sh
   ```

### Manual Deployment (Not Recommended)

If you need to deploy manually:
```bash
npx wrangler pages deploy site --project-name=podcast-graphs-web
```

**Note:** This skips validation and may fail if large files are present.

## Handling Large Files

If you encounter large summary files:

1. **Don't commit them to git** - They're already excluded by `.gitignore`
2. **Don't copy them to `site/`** - Keep them in `graphs/` only
3. **Exclude from deployment** - Add patterns to `.cfignore`
4. **Consider compression** - Reduce file size if the data is needed

### Large File Patterns

Common large files in this project:
- `*.csv` files (can be 100MB-1GB+)
- `*.json` files (can be gigabytes)
- Summary HTML files in `graphs/summaries/` (can be 25MB+)

These are already excluded from the `site/` deployment directory.

## Troubleshooting

### "Pages only supports files up to 25 MiB" Error

1. Run validation to find the culprit:
   ```bash
   uv run scripts/validate_deployment.py
   ```

2. Remove or exclude the large file(s)

3. Regenerate index.json (it may reference deleted files)

4. Deploy again

### Pre-commit Hook Not Working

Ensure it's executable:
```bash
chmod +x .git/hooks/pre-commit
```

### Bypassing Safeguards

**Don't do this** unless you know what you're doing:
- `git commit --no-verify` - Skips pre-commit hook
- Manual wrangler deploy - Skips validation

Both can result in failed deployments.

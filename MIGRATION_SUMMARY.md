# Migration Summary

## Date: 2026-03-06

## Overview
Migrated all graph/visualization code from `/Volumes/juan_mac_mini_ssd/podcast-conversations` to `/Volumes/juan_mac_mini_ssd/podcast-graphs-web`.

## Files Migrated

### Core Site Files
- `index.html` - Main landing page with episode listing
- `README.md` - Updated documentation

### Visualization Assets
- `graphs/` - All generated graph HTML, JSON, and CSV files (69 HTML files total)
- `lib/` - JavaScript dependencies:
  - `lib/bindings/utils.js` - Graph interaction utilities
  - `lib/tom-select/` - Dropdown UI library
  - `lib/vis-9.1.2/` - Network visualization library (vis.js)

### Scripts
- `scripts/build_site.py` - Build script for deployment
- `scripts/generate_entity_graphs.py` - Entity graph generation script

## Fixes Applied
- Fixed relative paths in nested graph HTML files:
  - Files in `graphs/summaries/` now use `../lib/` paths
  - Files in `graphs/podcast_name/` now use `../../lib/` paths

## File Structure
```
podcast-graphs-web/
├── index.html                 # Main landing page
├── graphs/
│   ├── summaries/            # Per-podcast summary graphs
│   └── [podcast_name]/       # Individual episode graphs
├── lib/
│   ├── bindings/
│   │   └── utils.js
│   ├── tom-select/
│   └── vis-9.1.2/
├── scripts/
│   ├── build_site.py
│   └── generate_entity_graphs.py
└── MIGRATION_SUMMARY.md      # This file
```

## Verification
- ✅ Web server running on http://localhost:8000
- ✅ Index page loads correctly
- ✅ Graph HTML files are accessible
- ✅ JavaScript dependencies load correctly
- ✅ Relative paths fixed for nested directories

## Total Assets
- 69 HTML graph visualizations
- 69 JSON graph data files
- 1 main index page
- 3 JavaScript libraries

# Podcast Conversation Graphs

Interactive network visualizations of entity relationships in podcast conversations. This static website automatically discovers and showcases conversation graphs with interactive search and exploration features.

## Features

- **🔍 Auto-Discovery**: Automatically detects and displays all graphs in `graphs/` directory - no manual HTML editing required
- **🌐 Interactive Graphs**: vis-network powered visualizations with force-directed layouts
- **🔎 Search & Filter**: Find episodes by title across all shows in real-time
- **🎨 Entity Legend**: Color-coded Person/Place nodes with relationship connections
- **📊 Graph Statistics**: Display counts of people, places, and connections
- **📱 Responsive Design**: Works seamlessly on desktop and mobile
- **🌙 Dark Theme**: Modern dark UI with gradient backgrounds
- **⚡ Zero Maintenance**: Add new graphs simply by running the generation script
- **🚀 Fast Performance**: Served from Cloudflare CDN with global distribution
- **💰 Free Hosting**: $0 cost on Cloudflare Pages free tier
- **🔄 Auto-Deploy**: Automatic deployments on git push
- **🔒 HTTPS Included**: Free SSL/TLS encryption

## Quick Start

### Prerequisites

- Python 3.12+ with `uv` package manager
- GitHub account (for deployment)
- Cloudflare account (free tier, for hosting)

### Generate and View Graphs Locally

```bash
# Generate graphs from transcripts (outputs to graphs/)
uv run scripts/generate_entity_graphs.py

# Start local server
python3 -m http.server 8000

# Open http://localhost:8000 in your browser
```

That's it! The web app automatically discovers all graphs in the `graphs/` directory.

## Project Structure

```
podcast-graphs-web/
├── index.html                  # Landing page with dynamic episode browser
├── index.json                  # Auto-generated graph index (updated by scripts)
├── graphs/                     # Interactive graph visualizations
│   ├── <show_name>/            # Per-show episode graphs
│   └── summaries/              # Show summary graphs
├── lib/                        # JavaScript dependencies
│   ├── bindings/utils.js       # Graph interaction utilities
│   ├── tom-select/             # Enhanced dropdown UI library
│   └── vis-9.1.2/              # Network visualization library
├── scripts/                    # Generation and build scripts
│   ├── generate_entity_graphs.py  # Entity graph generation (auto-updates index)
│   ├── generate_index.py       # Graph index generator
│   └── utils/                  # Utility modules
├── README.md                   # This file
├── pyproject.toml              # Python dependencies
└── uv.lock                     # Dependency lock file
```

### Graph File Formats

Each podcast episode generates three file formats:
- `.html` - Interactive visualization (displayed on the site)
- `.json` - Raw structured graph data
- `.csv` - Adjacency matrix export

Only HTML files are linked from the index page.

## How It Works

### Automatic Graph Discovery

The web app uses a two-step process to automatically discover and display graphs:

1. **Index Generation** (`scripts/generate_index.py`):
   - Scans the `graphs/` directory recursively
   - Finds all `*_graph.html` files
   - Organizes them by show
   - Generates `index.json` with metadata

2. **Dynamic Display** (`index.html`):
   - Fetches `index.json` on page load
   - Dynamically generates show sections and episode cards
   - No hardcoded episode lists needed

### Workflow

```
Transcripts → generate_entity_graphs.py → graphs/
                         ↓
              generate_index.py → index.json
                         ↓
                   index.html → User's Browser
```

## Generating Graphs

### From Transcript Files

```bash
# Process all transcripts in default directory
uv run scripts/generate_entity_graphs.py

# Process specific directory
uv run scripts/generate_entity_graphs.py --input-dir path/to/transcripts

# Process specific shows only
uv run scripts/generate_entity_graphs.py --shows show_name_1 --shows show_name_2

# Force reprocessing of all files
uv run scripts/generate_entity_graphs.py --force

# Generate with visualizations
uv run scripts/generate_entity_graphs.py --visualize
```

### Script Options

The `generate_entity_graphs.py` script accepts these options:

- `--input-dir` or `-d`: Recursively process all subdirectories as shows
- `--input` or `-i`: Process a specific file or directory
- `--output-dir`: Output directory (default: `graphs/`)
- `--shows`: Process only specific shows (can be repeated)
- `--force`: Force reprocessing of existing files
- `--visualize`: Generate interactive HTML visualizations
- `--spacy-model`: spaCy NER model (default: `en_core_web_lg`)

The script automatically:
1. Extracts PERSON and PLACE entities using spaCy NER
2. Builds directed graphs modeling movement between places
3. Generates per-episode and per-show summary graphs
4. Outputs JSON, CSV, and HTML formats
5. Updates `index.json` for the web app

### Manual Index Regeneration

The index is automatically updated after graph generation. To manually regenerate:

```bash
uv run scripts/generate_index.py
```

## Deployment

### Deploy to Cloudflare Pages

#### Step 1: Push to GitHub

```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit: podcast conversation graphs"

# Create GitHub repo using gh CLI
gh repo create podcast-graphs-web --public --source=. --remote=origin
git push -u origin main

# Or without gh CLI:
# 1. Create repo at https://github.com/new
# 2. Run: git remote add origin https://github.com/YOUR_USERNAME/podcast-graphs-web.git
# 3. Run: git push -u origin main
```

#### Step 2: Connect to Cloudflare Pages

1. Go to https://dash.cloudflare.com/
2. Click **Pages** → **Create a project** → **Connect to Git**
3. Authorize GitHub and select `podcast-graphs-web`
4. Configure settings:
   - **Production branch**: `main`
   - **Build command**: (leave empty)
   - **Build output directory**: `/`
   - **Root directory**: (leave empty)
5. Click **Save and Deploy**

Your site will be live at `https://podcast-graphs-web.pages.dev` in 2-3 minutes.

#### Step 3: Add Custom Domain (Optional)

1. In your Cloudflare Pages project, click **Custom domains**
2. Click **Set up a custom domain**
3. Enter your domain (e.g., `graphs.yourdomain.com`)
4. Cloudflare automatically configures DNS and provisions SSL

Live in 2-3 minutes at your custom domain with HTTPS!

### Alternative: Deploy with Wrangler CLI

```bash
# Install Wrangler
npm install -g wrangler

# Authenticate
wrangler login

# Deploy
wrangler pages deploy . --project-name=podcast-graphs

# Add custom domain (optional)
wrangler pages domain add podcast-graphs graphs.yourdomain.com
```

## Updating Graphs

The web app automatically discovers new graphs - no manual HTML editing needed!

### Simple Update Workflow

```bash
# 1. Generate new graphs (automatically updates index.json)
uv run scripts/generate_entity_graphs.py

# 2. Commit and deploy
git add .
git commit -m "Add new episodes"
git push  # Auto-deploys to Cloudflare if connected
```

That's it! New graphs appear automatically on your site.

### What Happens Automatically

When you run `generate_entity_graphs.py`:
1. Processes transcript files and generates graphs in `graphs/`
2. Automatically runs `generate_index.py` to update the catalog
3. `index.json` is regenerated with all discovered graphs
4. Web app fetches the updated index and displays new content

## Local Development

### Test Locally

```bash
# Using Python's built-in server
python3 -m http.server 8000

# Or using Node.js
npx serve .
```

Open http://localhost:8000 to view the site.

### Sample URLs

- **Landing page**: http://localhost:8000/
- **Summary graph**: http://localhost:8000/graphs/summaries/a_bit_fruity_with_matt_bernstein_graph.html
- **Episode graph**: http://localhost:8000/graphs/a_bit_fruity_with_matt_bernstein/introducing_a_bit_fruity_with_matt_bernstein_graph.html

## Technical Details

### Entity Graph Generation

The graph generation process uses:

- **spaCy NER**: Extracts PERSON and PLACE entities from transcripts
- **NetworkX**: Builds directed graphs modeling entity relationships
- **PyVis**: Generates interactive HTML visualizations

#### Graph Structure

- **Nodes**: PERSON and PLACE entities
- **Edges**: Two types of relationships:
  - **Association**: Person ↔ Place (person mentioned with a place)
  - **Movement**: Place → Place (person moves from one place to another)

#### Entity Resolution

The script performs multi-pass entity normalization:
1. **Episode-level**: Resolves partial names and abbreviations within each episode
2. **Show-level**: Cross-episode normalization for consistent entity naming
3. **Deduplication**: Removes overlapping entities (e.g., entity tagged as both PERSON and PLACE)

### Web App Components

#### Landing Page (`index.html`)
- Fetches `index.json` on load
- Dynamically generates show sections and episode cards
- Real-time search across all episodes
- Responsive card-based layout
- Dark theme with gradient backgrounds

#### Graph Visualizations
- Interactive network graphs using vis.js 9.1.2
- Color-coded nodes (Person: blue, Place: orange)
- Edge colors indicate relationship type
- Hover interactions show node/edge details
- Force-directed physics layout
- Zoom and pan controls

#### JavaScript Dependencies
- **vis-network 9.1.2**: Network visualization
- **Bootstrap 5.0.0-beta3**: UI framework (loaded from CDN)
- **Custom utils.js**: Graph interaction utilities

### Performance

- **Total size**: ~6-8 MB (varies by content)
- **Load time**: < 2s on fast connections
- **CDN**: Global Cloudflare network
- **Caching**: Automatic via Cloudflare

### Optimization Tips

1. **Reduce file size**: Only deploy HTML files, exclude CSV/JSON
   ```bash
   # In .gitignore
   graphs/**/*.csv
   graphs/**/*.json
   ```

2. **Cloudflare automatic optimizations**:
   - HTML minification
   - Asset compression (gzip/brotli)
   - Image optimization
   - Cache-Control headers

## Troubleshooting

### Graphs not displaying

**Problem**: Index page loads but no episodes appear.

**Solution**:
```bash
# Regenerate the index
uv run scripts/generate_index.py

# Check browser console for errors
# Verify index.json exists and is valid JSON
cat index.json | python3 -m json.tool
```

### Index.json not found

**Problem**: `Failed to load index.json` error in browser.

**Solution**:
```bash
# Generate the index
uv run scripts/generate_index.py

# Verify it exists
ls -lh index.json
```

### Graphs load but don't render

**Problem**: HTML files load but graphs are blank.

**Solution**:
- Ensure `lib/` directory is present with all dependencies
- Check browser console for JavaScript errors
- Verify relative paths in graph HTML files:
  - `graphs/summaries/*.html` → `../lib/`
  - `graphs/show_name/*.html` → `../../lib/`

### 404 errors on episode links

**Problem**: Clicking episodes returns 404.

**Solution**:
- Verify file paths in `index.json` match actual files
- Check that graph HTML files exist in expected locations
- Ensure relative paths are correct

### Deployment fails

**Problem**: Cloudflare Pages build fails.

**Solution**:
- Check build logs in Cloudflare dashboard
- Verify repository size < 25 MB
- Ensure all files are committed (check `.gitignore`)
- Confirm `lib/` directory is included

### Custom domain not working

**Problem**: Domain shows "Not found" error.

**Solution**:
1. Wait 1-5 minutes for DNS propagation
2. Verify DNS records in Cloudflare DNS dashboard
3. Check SSL certificate status
4. Try `https://` instead of `http://`
5. Clear browser cache

## Cost & Limits

### Cloudflare Pages Free Tier

- ✅ **500 builds/month** (plenty for regular updates)
- ✅ **Unlimited requests**
- ✅ **Unlimited bandwidth**
- ✅ **100 GB-seconds compute**
- ✅ **1 concurrent build**

Your site comfortably stays within free tier limits.

## Security

- **HTTPS**: Automatic SSL/TLS encryption
- **DDoS Protection**: Cloudflare's network
- **No backend**: Static site, no server-side code
- **No secrets**: All data is meant to be public

## Analytics (Optional)

Enable Cloudflare Web Analytics:
1. Go to your Pages project in Cloudflare dashboard
2. Click **Analytics** tab
3. Enable **Web Analytics**
4. View traffic stats, page views, and performance metrics

## Backup Strategy

Your site is backed up in multiple locations:
1. **Local**: Your development machine
2. **GitHub**: Remote repository with full history
3. **Cloudflare**: Last 100 deployments preserved

## Common Commands

```bash
# Generate graphs from transcripts
uv run scripts/generate_entity_graphs.py

# Regenerate index manually
uv run scripts/generate_index.py

# Test locally
python3 -m http.server 8000

# Deploy changes
git add .
git commit -m "Update graphs"
git push
```

## Resources

- [Cloudflare Pages Documentation](https://developers.cloudflare.com/pages/)
- [vis-network Documentation](https://visjs.github.io/vis-network/docs/network/)
- [spaCy NER Documentation](https://spacy.io/usage/linguistic-features#named-entities)
- [NetworkX Documentation](https://networkx.org/documentation/stable/)

## Known Limitations

- Requires running Python scripts to generate new graphs
- Static site - no server-side filtering or dynamic data loading
- Graph files can be large for episodes with many entities

## Future Enhancements

Potential improvements:
- [ ] Add filters for entity types (Person/Place)
- [ ] Export functionality (download CSV/JSON from UI)
- [ ] Timeline visualization of entity mentions
- [ ] Cross-episode entity tracking
- [ ] Advanced search (by entity, date range, etc.)
- [ ] Graph comparison view

## License

This project is for personal/educational use.

---

**Status**: ✅ Production Ready

The podcast graphs web app is fully functional with automatic graph discovery and zero-maintenance updates.

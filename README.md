# Podcast Conversation Graphs

Interactive network visualizations of entity relationships in podcast conversations. This static website automatically discovers and showcases conversation graphs with interactive search and exploration features.

## TL;DR - Quick Workflow

```bash
# 1. Setup (one-time)
uv sync && uv run python -m spacy download en_core_web_lg

# 2. Generate graphs from transcripts
uv run scripts/generate_entity_graphs.py --visualize

# 3. Preview locally
python3 -m http.server 8000  # Visit http://localhost:8000

# 4. Deploy to production
git add . && git commit -m "New episodes" && git push
```

After Cloudflare Pages setup, every `git push` automatically deploys your site. No build commands, no configuration needed.

## Features

- **🔍 Auto-Discovery**: Automatically detects and displays all graphs in `graphs/` directory - no manual HTML editing required
- **🌐 Interactive Graphs**: vis-network powered visualizations with force-directed layouts
- **💬 Rich Narrative Context**: Graph edges display actual transcript quotes, speaker attribution, and temporal markers
- **😊 Sentiment Visualization**: Color-coded edges (green/red/gray) based on emotional tone with distribution charts
- **🏷️ Topic Clustering**: Cross-episode semantic clustering to identify themes and group similar content
- **📚 Topic Browser**: Collapsible sidebar showing all topics with keywords, clusters, and episode lists
- **🔎 Search & Filter**: Find episodes by title, type, or topic across all shows in real-time
- **🎨 Entity Legend**: Color-coded Person/Place nodes with sentiment-based edge colors
- **📊 Graph Statistics**: Display counts of people, places, connections, and sentiment distribution
- **🎯 Enhanced Tooltips**: Hover over relationships to see who discussed them, when, sentiment, and actual conversation excerpts
- **📱 Responsive Design**: Works seamlessly on desktop and mobile
- **🎭 Multi-Level Filtering**: Combine search, type filters, and topic filters simultaneously
- **🌙 Dark Theme**: Modern dark UI with gradient backgrounds
- **⚡ Zero Maintenance**: Add new graphs simply by running the generation script
- **🚀 Fast Performance**: Served from Cloudflare CDN with global distribution
- **💰 Free Hosting**: $0 cost on Cloudflare Pages free tier
- **🔄 Auto-Deploy**: Automatic deployments on git push
- **🔒 HTTPS Included**: Free SSL/TLS encryption

## Quick Start

### Prerequisites

- Python 3.10+ with `uv` package manager
- GitHub account (for deployment)
- Cloudflare account (free tier, for hosting)

### Installation & Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/podcast-graphs-web.git
cd podcast-graphs-web

# Install dependencies with uv (automatically creates virtual environment)
uv sync

# Download the spaCy language model
uv run python -m spacy download en_core_web_lg
```

### Generate and View Graphs Locally

```bash
# Generate graphs from transcripts (outputs to graphs/)
uv run scripts/generate_entity_graphs.py --visualize

# Note: First run will download the sentiment model (~250MB)
# You'll see some 404 warnings - these are normal and can be ignored

# Start local server
python3 -m http.server 8000

# Open http://localhost:8000 in your browser
```

That's it! The web app automatically discovers all graphs in the `graphs/` directory.

### Deployment Summary

**After initial Cloudflare Pages setup** (one-time, see [Deployment](#deployment) section):

1. Generate graphs: `uv run scripts/generate_entity_graphs.py --visualize`
2. Commit changes: `git add . && git commit -m "New episodes"`
3. Deploy: `git push origin main`

**Done!** Site rebuilds automatically in 2-3 minutes. No manual build steps, no configuration files to edit.

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
├── pyproject.toml              # Python dependencies (managed by uv)
├── uv.lock                     # Dependency lock file
└── wrangler.toml               # Cloudflare Pages configuration
```

### Graph File Formats

Each podcast episode generates three file formats:
- `.html` - Interactive visualization (displayed on the site)
- `.json` - Raw structured graph data with sentiment-enhanced contexts
- `.csv` - Adjacency matrix export

Additionally, the script generates:
- `topics.json` - Cross-episode topic clustering results with episode-to-topic mappings

Only HTML files are linked from the index page.

### Topic Clustering Output

The `topics.json` file contains:

```json
{
  "topics": [
    {
      "topic_id": 0,
      "topic_words": ["election", "voting", "campaign", "democracy", "poll"],
      "topic_label": "election, voting, campaign",
      "episode_count": 12,
      "episodes": ["episode_1", "episode_5", ...]
    }
  ],
  "episode_topics": {
    "episode_name": {
      "topic_id": 0,
      "topic_words": ["election", "voting", "campaign"],
      "topic_label": "election, voting, campaign"
    }
  },
  "topic_info": [...]
}
```

This enables:
- Discovering recurring themes across your podcast catalog
- Finding episodes that discuss similar topics
- Understanding topical coverage and distribution
- Building topic-based navigation features

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

### Input Format

The script expects JSON transcript files with speaker labels in the following format:

```json
{
  "segments": [
    {
      "speaker": "SPEAKER_00",
      "speaker_name": "Rachel Maddow",
      "text": "Welcome to the show...",
      "start": 0.0,
      "end": 5.2
    },
    {
      "speaker": "SPEAKER_01",
      "speaker_name": "Guest Name",
      "text": "Thanks for having me...",
      "start": 5.5,
      "end": 10.0
    }
  ]
}
```

Required fields:
- `segments`: Array of conversation segments
- `text`: Transcript text for entity extraction
- `speaker` or `speaker_name`: For attribution (optional but recommended)
- `start`: Timestamp for temporal analysis (optional but recommended)

### From Transcript Files

```bash
# Process all transcripts in default directory (graphs/)
uv run scripts/generate_entity_graphs.py --visualize

# Process specific directory
uv run scripts/generate_entity_graphs.py --transcripts-dir path/to/transcripts --visualize

# Process specific shows only
uv run scripts/generate_entity_graphs.py --shows show_name_1 --shows show_name_2 --visualize

# Force reprocessing of all files
uv run scripts/generate_entity_graphs.py --force --visualize
```

### Script Options

The `generate_entity_graphs.py` script accepts these options:

- `--transcripts-dir`: Directory containing transcript JSON files (default: `graphs/`)
- `--output-dir`: Output directory for generated graphs (default: `graphs/`)
- `--shows`: Process only specific shows by name (can be repeated)
- `--force`: Force reprocessing of existing files (skip caching)
- `--visualize`: Generate interactive HTML visualizations (required for web viewing)
- `--spacy-model`: spaCy NER model to use (default: `en_core_web_lg`)

**Important**: Always use `--visualize` to generate the HTML files needed for the web app!

The script automatically:
1. Extracts PERSON and PLACE entities using spaCy NER
2. Captures context for each entity mention (text snippet, speaker, timestamp)
3. **Analyzes sentiment** of each context using `distilbert-base-uncased-finetuned-sst-2-english`
4. Builds directed graphs modeling relationships with rich narrative context
5. Calculates temporal positioning (early/middle/late in episode)
6. Generates semantically labeled edges with relationship types
7. Stores up to 3 context examples per relationship for tooltip display
8. **Clusters episodes by topics** using BERTopic for cross-episode theme discovery
9. Generates per-episode and per-show summary graphs
10. Outputs JSON, CSV, HTML formats, and topic metadata
11. Updates `index.json` for the web app

**Note**: During first run, the sentiment model will download automatically (~250MB). You may see 404 warnings for optional model files (tokenizer.json, added_tokens.json, etc.) - these are normal and can be safely ignored.

### Model Downloads & Caching

**First Run**:
- spaCy model: `en_core_web_lg` (~800MB) - manual download required
- Sentiment model: `distilbert-base-uncased-finetuned-sst-2-english` (~250MB) - auto-downloads
- BERTopic embeddings model - auto-downloads

**Subsequent Runs**:
- Models are cached in `~/.cache/huggingface/` and `~/.cache/torch/`
- Processing is much faster (no re-downloading)

### Manual Index Regeneration (Rarely Needed)

The index is automatically updated when you run `generate_entity_graphs.py`. You only need to manually regenerate if you've modified graph files directly:

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
   - **Build command**: (leave empty - no build needed, files are pre-generated)
   - **Build output directory**: `/` (deploy from root)
   - **Root directory**: (leave empty)
5. Click **Save and Deploy**

Your site will be live at `https://podcast-graphs-web.pages.dev` in 2-3 minutes.

**After setup, deployments are automatic**: Every `git push` to main triggers a new deployment. No manual intervention needed!

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

## Complete Workflow: Generate, Update & Deploy

The web app automatically discovers new graphs - no manual HTML editing needed!

### 1. Generate Graphs from Transcripts

```bash
# Generate graphs with interactive visualizations
uv run scripts/generate_entity_graphs.py --visualize

# Or force regenerate all graphs (skip cache)
uv run scripts/generate_entity_graphs.py --visualize --force

# Or process specific shows only
uv run scripts/generate_entity_graphs.py --visualize --shows show_name_1 --shows show_name_2
```

**What this does**:
- Extracts entities and builds graphs
- Performs sentiment analysis on all contexts
- Clusters episodes by topics using BERTopic
- Generates HTML visualizations in `graphs/` directory
- Creates `topics.json` with theme metadata
- Automatically updates `index.json`

### 2. Preview Locally (Optional)

```bash
# Start local server
python3 -m http.server 8000

# Open http://localhost:8000 in your browser
```

### 3. Deploy to Cloudflare Pages

```bash
# Commit your changes
git add graphs/ index.json index.html
git commit -m "Add new episodes with sentiment analysis and topic clustering

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Push to GitHub (auto-deploys if Cloudflare Pages is connected)
git push origin main
```

**That's it!** Your site will automatically rebuild and deploy in 2-3 minutes.

### What Gets Deployed

- ✅ `index.html` - Landing page
- ✅ `index.json` - Graph metadata
- ✅ `graphs/` - All HTML visualizations
- ✅ `lib/` - JavaScript dependencies
- ❌ CSV and JSON data files (excluded via .gitignore for size optimization)

### What Happens During Graph Generation

When you run `generate_entity_graphs.py --visualize`:
1. Extracts PERSON and PLACE entities from transcript text using spaCy NER
2. Captures context snippets, speakers, and timestamps for each mention
3. Analyzes sentiment of each context using DistilBERT (positive/negative/neutral)
4. Builds directed graphs with semantically labeled relationships
5. Performs cross-episode topic clustering using BERTopic
6. Generates interactive HTML visualizations with rich tooltips and sentiment colors
7. Creates JSON and CSV exports for data analysis
8. Outputs files to `graphs/` directory organized by show
9. Generates `topics.json` with theme metadata
10. Automatically updates `index.json` for the web app

**No separate index generation needed** - `generate_entity_graphs.py` handles everything!

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

## Using the Visualizations

### Sentiment Visualization in Graphs

**Edge Colors:**
- 🟢 **Green edges**: Positive sentiment relationships (discussed favorably)
- 🔴 **Red edges**: Negative sentiment relationships (discussed critically)
- ⚪ **Gray edges**: Neutral sentiment relationships

**Sentiment Distribution Chart:**
Located in the graph header, shows the emotional tone breakdown:
- Bar chart with percentage breakdown
- Counts for each sentiment category
- Example: "😊 12 (45.2%), 😞 8 (30.1%), 😐 7 (24.7%)"

### Topic Browser & Filtering

**Access Topics:**
1. Click the floating "📚 Topics" button (bottom right)
2. Sidebar slides in showing all discovered topics

**Browse Topics:**
- Each topic cluster shows:
  - Topic label (top keywords)
  - Episode count
  - Related keywords
  - List of episodes (click to expand)
- Click a topic cluster to filter episodes by that theme

**Filter by Topic:**
- Use topic filter chips in the navigation bar
- Click topic tags on episode cards
- Click topics in the sidebar browser
- Combine with search and type filters

### Enhanced Tooltip Example

When hovering over a relationship edge in the graph, you'll see rich context like:

```
📍 Donald Trump → Mar-a-Lago
━━━━━━━━━━━━━━━━━━━━
Relationship: Mentioned In
Mentions: 5
Discussed by: Rachel Maddow, Guest Speaker

💬 Context:

[EARLY] 😞 Rachel Maddow:
  "Trump was at Mar-a-Lago when the indictment was announced, surrounded by his legal team..."
  Sentiment: NEGATIVE

[LATE] 😐 Guest Speaker:
  "The documents were allegedly stored at Mar-a-Lago in unsecured locations..."
```

This provides immediate insight into:
- **What** the relationship is (mentioned in a place)
- **How often** it occurred (5 times)
- **Who** discussed it (Rachel Maddow, Guest Speaker)
- **When** in the episode (early vs. late)
- **Sentiment** of the discussion (positive 😊, negative 😞, or neutral 😐)
- **Evidence** from actual transcript excerpts

## Technical Details

### Entity Graph Generation

The graph generation process uses:

- **spaCy NER** (`>=3.7.0`): Extracts PERSON and PLACE entities from transcripts
- **NetworkX** (`>=3.0`): Builds directed graphs modeling entity relationships
- **PyVis** (`>=0.3.0`): Generates interactive HTML visualizations
- **Transformers** (`>=4.30.0`) + **PyTorch** (`>=2.0.0`): Sentiment analysis pipeline
- **BERTopic** (`>=0.15.0`): Cross-episode topic clustering and theme discovery
- **Polars** (`>=0.20.0`): Fast data processing
- **scikit-learn** (`>=1.3.0`): Supporting ML utilities for clustering

#### Graph Structure

- **Nodes**: PERSON and PLACE entities with color coding (Person: blue, Place: orange)
- **Edges**: Semantically labeled relationships with rich narrative context:
  - **mentioned_in**: Person ↔ Place (person discussed in context of a place)
  - **traveled_to**: Place → Place (person moves from one place to another)

Each edge captures:
- **Relationship type**: Semantic label describing the connection
- **Weight**: Number of times the relationship occurs
- **Speakers**: List of people who discussed this relationship
- **Context examples**: Up to 3 actual transcript quotes showing where the relationship occurs
- **Temporal markers**: When in the episode (early/middle/late) each mention happens
- **Timestamps**: Exact timing of each context example

#### Entity Resolution

The script performs multi-pass entity normalization:
1. **Episode-level**: Resolves partial names and abbreviations within each episode
2. **Show-level**: Cross-episode normalization for consistent entity naming
3. **Deduplication**: Removes overlapping entities (e.g., entity tagged as both PERSON and PLACE)

#### Rich Annotation Pipeline

The enhanced annotation system captures narrative context at multiple levels:

1. **Context Extraction** (during entity processing):
   - Text snippet (200 char max) showing surrounding conversation
   - Speaker attribution from transcript metadata
   - Segment index for temporal positioning
   - Timestamp for precise timing

2. **Temporal Analysis** (during graph building):
   - Calculates position within episode (0-100%)
   - Categorizes as early (<33%), middle (33-66%), or late (>66%)
   - Enables understanding of narrative flow

3. **Relationship Modeling**:
   - Semantic labeling (e.g., "mentioned_in", "traveled_to")
   - Weight calculation (number of co-occurrences)
   - Speaker aggregation across mentions
   - Context storage (up to 3 examples per edge)

4. **Sentiment Analysis**:
   - Uses `distilbert-base-uncased-finetuned-sst-2-english` (DistilBERT fine-tuned on Stanford Sentiment Treebank)
   - Classifies each context as POSITIVE, NEGATIVE, or NEUTRAL
   - Confidence scores for sentiment predictions
   - Visual indicators with emojis (😊 positive, 😞 negative, 😐 neutral)
   - Cached model loading for performance
   - Note: 404 warnings during model loading (for optional files) are expected and non-critical

5. **Topic Clustering** (cross-episode):
   - BERTopic-based semantic clustering
   - Automatic topic number detection
   - Extracts top keywords for each topic
   - Episode-to-topic mappings with labels
   - Identifies themes across entire show catalogs
   - Generates `topics.json` with full metadata

6. **Tooltip Generation**:
   - Formatted display with emojis and structure
   - Temporal markers showing conversation progression
   - Sentiment indicators for emotional context
   - Actual quotes providing evidence for relationships
   - Speaker attribution for accountability

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
- Edge colors indicate relationship type (associations vs. movements)
- Rich hover tooltips showing:
  - Relationship type and mention count
  - Speakers who discussed the relationship
  - 1-2 actual transcript excerpts with temporal markers
  - Context showing when in the conversation it occurred
- Force-directed physics layout with smooth animations
- Zoom and pan controls for exploration
- Responsive sizing adapting to viewport height

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

1. **Reduce file size**: Only deploy HTML files, exclude large data files
   ```bash
   # In .gitignore
   graphs/**/*.csv
   graphs/**/*.json
   *.csv
   *.json

   # EXCEPTION: Keep index.json (required for site to function)
   !index.json

   # Exclude very large summary graphs (>25 MB causes deployment issues)
   site/graphs/summaries/*.html
   ```

2. **Cloudflare Pages limits**:
   - Maximum file size: 25 MB
   - Large summary graphs should be excluded from deployment
   - Individual episode graphs are typically well under the limit

3. **Cloudflare automatic optimizations**:
   - HTML minification
   - Asset compression (gzip/brotli)
   - Image optimization
   - Cache-Control headers

## Troubleshooting

### Sentiment model 404 warnings

**Problem**: When running `generate_entity_graphs.py`, you see HTTP 404 errors for files like `tokenizer.json`, `added_tokens.json`, `special_tokens_map.json`.

**Solution**: These warnings are **normal and expected**. The DistilBERT model uses an older tokenizer format (`vocab.txt`) and doesn't include these optional files. The transformers library gracefully handles their absence by using defaults. Your sentiment analysis will work perfectly fine.

Example of expected (non-critical) warnings:
```
INFO HTTP Request: HEAD https://huggingface.co/.../tokenizer.json "HTTP/1.1 404 Not Found"
INFO HTTP Request: HEAD https://huggingface.co/.../added_tokens.json "HTTP/1.1 404 Not Found"
INFO HTTP Request: HEAD https://huggingface.co/.../special_tokens_map.json "HTTP/1.1 404 Not Found"
```

**What matters**: Model weights loading successfully (100%) and `tokenizer_config.json` + `vocab.txt` returning 200 OK.

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

## Quick Reference

### Essential Commands

```bash
# 1. GENERATE: Create graphs from transcripts
uv run scripts/generate_entity_graphs.py --visualize

# 2. PREVIEW: Test locally before deploying
python3 -m http.server 8000  # Open http://localhost:8000

# 3. DEPLOY: Push to production
git add graphs/ index.json index.html
git commit -m "Add new episodes"
git push origin main  # Auto-deploys to Cloudflare Pages
```

### Advanced Options

```bash
# Force regenerate all graphs (skip cache)
uv run scripts/generate_entity_graphs.py --visualize --force

# Process specific shows only
uv run scripts/generate_entity_graphs.py --visualize --shows "show_name_1" --shows "show_name_2"

# Custom transcript directory
uv run scripts/generate_entity_graphs.py --transcripts-dir path/to/transcripts --visualize

# Manually regenerate index (usually not needed, auto-updated by generate script)
uv run scripts/generate_index.py

# Deploy without git push (using Wrangler CLI)
npx wrangler pages deploy . --project-name=podcast-graphs
```

### Typical Workflow

```bash
# Add new transcript JSON files to your transcripts directory
# Then run:

uv run scripts/generate_entity_graphs.py --visualize   # Generate graphs + update index
python3 -m http.server 8000                            # Preview locally
git add . && git commit -m "New episodes" && git push  # Deploy
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

## Current Features (v0.1.0)

### Graph Analysis & Visualization
- ✅ **Entity extraction** - spaCy NER for PERSON and PLACE entities
- ✅ **Sentiment analysis** - DistilBERT-based emotion detection (positive/negative/neutral)
- ✅ **Sentiment visualization** - Color-coded edges with distribution charts
- ✅ **Topic clustering** - BERTopic-based semantic clustering across episodes
- ✅ **Rich tooltips** - Hover shows speakers, sentiment, temporal markers, and quotes
- ✅ **Temporal markers** - Track when in episodes relationships occur (early/middle/late)
- ✅ **Interactive graphs** - vis-network with zoom, pan, force-directed layout

### Web Interface
- ✅ **Auto-discovery** - Automatically detects all graphs in `graphs/` directory
- ✅ **Topic browser** - Collapsible sidebar with clusters, keywords, episodes
- ✅ **Multi-level filtering** - Combine search, type, and topic filters
- ✅ **Responsive design** - Works on desktop and mobile
- ✅ **Dark theme** - Modern UI with gradient backgrounds

### Deployment & Performance
- ✅ **Zero-config deployment** - Push to GitHub, auto-deploys to Cloudflare Pages
- ✅ **Global CDN** - Served from Cloudflare's edge network
- ✅ **Free hosting** - $0 cost on Cloudflare Pages free tier
- ✅ **Automatic HTTPS** - Free SSL/TLS encryption included

## Future Enhancements

Potential improvements:
- [ ] Add filters for entity types (Person/Place)
- [ ] Add filters by sentiment (positive/negative/neutral relationships)
- [ ] Topic-based navigation UI (browse episodes by topic)
- [ ] Export functionality (download CSV/JSON from UI)
- [ ] Timeline visualization of entity mentions
- [ ] Cross-episode entity tracking
- [ ] Advanced search (by entity, date range, sentiment, topic)
- [ ] Graph comparison view (compare episode graphs side-by-side)
- [ ] Sentiment trend analysis over time
- [ ] Interactive topic exploration dashboard

## License

This project is for personal/educational use.

---

**Status**: ✅ Production Ready

The podcast graphs web app is fully functional with automatic graph discovery and zero-maintenance updates.

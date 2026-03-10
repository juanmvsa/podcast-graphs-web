# Podcast Conversation Graphs

Interactive network visualizations of entity relationships in podcast conversations. Extracts people and places from transcripts, analyzes sentiment, clusters episodes by topic, and generates interactive graph visualizations — all served as a static site.

## TL;DR — Quick Workflow

```bash
# 1. Setup (one-time)
uv sync && uv pip install en-core-web-lg@https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl

# 2. Generate graphs with sentiment analysis, topic clustering, and HTML visualizations
uv run scripts/generate_entity_graphs.py --visualize --force

# 3. Preview locally
python3 -m http.server 8000  # Visit http://localhost:8000

# 4. Deploy to production
./scripts/deploy.sh
```

## Features

- **🌐 Interactive Graphs** — vis-network force-directed layouts with zoom, pan, and drag
- **😊 Sentiment Analysis** — Color-coded edges (green/red/gray) with distribution charts using DistilBERT
- **🏷️ Topic Clustering** — Cross-episode semantic clustering via BERTopic with topic browser sidebar
- **💬 Rich Context** — Hover tooltips show transcript quotes, speakers, temporal markers, and sentiment
- **🔎 Search & Filter** — Real-time search, show/type/topic filters that combine freely
- **📱 Responsive** — Works on desktop and mobile with dark theme
- **⚡ Zero Maintenance** — Run one script to regenerate everything; push to deploy

## Project Structure

```
podcast-graphs-web/
├── index.html                  # Landing page with dynamic episode browser
├── index.json                  # Auto-generated catalog (shows, episodes, topics)
├── graphs/                     # Generated graph files
│   ├── <show_name>/            # Per-show directory
│   │   ├── *_graph.html        # Interactive HTML visualizations
│   │   ├── *_graph.json        # Structured graph data (edges with sentiment/contexts)
│   │   └── *_graph.csv         # Adjacency matrix export
│   ├── summaries/              # Show-level and topic-level summary graphs
│   │   ├── <show>_graph.*      # Merged show summary
│   │   └── <show>/topics_*_graph.*  # Per-topic summaries
│   └── topics.json             # Cross-episode topic clustering metadata
├── transcripts_.../            # Transcript JSON files (input, one subdir per show)
├── lib/                        # JavaScript dependencies (vis-network, etc.)
├── scripts/
│   ├── generate_entity_graphs.py  # Main pipeline: NER → graphs → sentiment → topics
│   ├── generate_index.py       # Scans graphs/ → index.json
│   ├── build_site.py           # Copies files to site/ for deployment
│   ├── deploy.sh               # Clean deploy wrapper (Cloudflare Pages)
│   └── clean.sh                # Cache cleanup
├── site/                       # Deployment directory (Cloudflare Pages serves this)
├── pyproject.toml              # Python dependencies (managed by uv)
├── uv.lock                     # Dependency lock file
└── wrangler.toml               # Cloudflare Pages config (output dir: site/)
```

## Prerequisites

- **Python 3.10+** with [`uv`](https://docs.astral.sh/uv/) package manager
- **GitHub account** (for deployment)
- **Cloudflare account** (free tier, for hosting)

## Setup

```bash
# Clone and install dependencies
git clone https://github.com/YOUR_USERNAME/podcast-graphs-web.git
cd podcast-graphs-web
uv sync

# Download spaCy language model (~800 MB, one-time)
# Note: `spacy download` requires pip, which uv doesn't provide, so install directly:
uv pip install en-core-web-lg@https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl
```

On first pipeline run, the sentiment model (~250 MB) and topic-embedding model (~80 MB) download automatically. Models are cached in `~/.cache/huggingface/`.

## Generating Graphs

### Input Format

Place transcript JSON files in subdirectories under the transcripts directory (one subdirectory per show). Each file must have this structure:

```json
{
  "segments": [
    {
      "speaker": "SPEAKER_00",
      "speaker_name": "Rachel Maddow",
      "text": "Welcome to the show...",
      "start": 0.0,
      "end": 5.2
    }
  ]
}
```

Required: `segments[].text`. Recommended: `speaker`/`speaker_name` (for attribution), `start` (for temporal analysis).

### Running the Pipeline

```bash
# Generate graphs for ALL shows (with HTML visualizations)
uv run scripts/generate_entity_graphs.py --visualize

# Process specific shows only
uv run scripts/generate_entity_graphs.py --visualize \
  --shows a_bit_fruity_with_matt_bernstein \
  --shows the_ezra_klein_show

# Force regenerate everything (ignore cache / existing outputs)
uv run scripts/generate_entity_graphs.py --visualize --force

# Custom transcript directory
uv run scripts/generate_entity_graphs.py --visualize \
  --transcripts-dir /path/to/transcripts
```

### CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--transcripts-dir` | `transcripts_with_speaker_labels_postprocessed_with_utterance_and_document_labels/` | Input directory with transcript JSON files |
| `--output-dir` | `graphs/` | Output directory for generated graphs |
| `--shows` | (all shows) | Process only named shows (repeatable) |
| `--visualize` | off | **Required for web app** — generates interactive HTML files |
| `--force` | off | Reprocess episodes even if output already exists |
| `--spacy-model` | `en_core_web_lg` | spaCy NER model |

> **Important:** Always pass `--visualize` if you want HTML files for the web app.
> Use `--force` when re-running after pipeline bug fixes to regenerate existing outputs.

### What the Pipeline Produces

For each episode transcript:
| File | Contents |
|------|----------|
| `*_graph.json` | Nodes, edges with `contexts` (sentiment, speakers, temporal markers) |
| `*_graph.html` | Interactive vis-network visualization (only with `--visualize`) |
| `*_graph.csv` | Adjacency matrix |

For each show:
| File | Contents |
|------|----------|
| `summaries/<show>_graph.*` | Merged summary graph across all episodes |
| `summaries/<show>/topics_*_graph.*` | Per-topic summary graphs |

Global:
| File | Contents |
|------|----------|
| `graphs/topics.json` | Topic clusters, keywords, episode-to-topic mappings |
| `index.json` | Catalog of all shows/episodes/summaries for the frontend |

### Manual Index Regeneration

The pipeline auto-updates `index.json`. Only run this manually if you've moved or deleted graph files by hand:

```bash
uv run scripts/generate_index.py
```

## Deployment

Deployment uses Cloudflare Pages with the `site/` directory as the build output (configured in `wrangler.toml`).

### Step 1: Build the Site

After generating graphs, copy everything into the `site/` deployment directory:

```bash
# Copy index.html, lib/, and all graph files into site/
uv run scripts/build_site.py
```

This copies `index.html` → `site/index.html`, `lib/` → `site/lib/`, and `graphs/` → `site/graphs/`.

### Step 2: Deploy

**Option A — Git push (auto-deploy)**

After one-time Cloudflare Pages setup (see below), every push to `main` auto-deploys:

```bash
git add site/ index.json graphs/topics.json
git commit -m "Add new episodes"
git push origin main
```

**Option B — Wrangler CLI (manual deploy)**

```bash
./scripts/deploy.sh
# or directly:
npx wrangler pages deploy site --project-name=podcast-graphs-web
```

### One-Time: Connect to Cloudflare Pages

1. Go to https://dash.cloudflare.com/ → **Pages** → **Create a project** → **Connect to Git**
2. Select the `podcast-graphs-web` repository
3. Configure:
   - **Production branch**: `main`
   - **Build command**: (leave empty — files are pre-built)
   - **Build output directory**: `site`
4. Click **Save and Deploy**

Site goes live at `https://podcast-graphs-web.pages.dev` in ~2 minutes.

### Custom Domain (Optional)

In your Pages project → **Custom domains** → add your domain. Cloudflare handles DNS + SSL automatically.

## Complete Workflow (End to End)

```bash
# 1. Generate graphs with full data (sentiment, topics, HTML visualizations)
uv run scripts/generate_entity_graphs.py --visualize

# 2. Preview locally
python3 -m http.server 8000   # → http://localhost:8000

# 3. Build the deployment directory
uv run scripts/build_site.py

# 4. Deploy
git add . && git commit -m "New episodes" && git push
# Or: ./scripts/deploy.sh
```

### Adding New Episodes

1. Drop new transcript JSON files into the appropriate show subdirectory under the transcripts directory
2. Run the pipeline — it only processes new (unprocessed) episodes by default
3. Build site + deploy

### Regenerating All Data

If you've fixed a bug in the pipeline or want to refresh everything:

```bash
uv run scripts/generate_entity_graphs.py --visualize --force
uv run scripts/build_site.py
./scripts/deploy.sh
```

## Using the Visualizations

### Graph Colors

| Element | Meaning |
|---------|---------|
| 🔵 Blue node | Person entity |
| 🟠 Orange node | Place entity |
| 🟢 Green edge | Positive sentiment |
| 🔴 Red edge | Negative sentiment |
| ⚪ Gray edge | Neutral sentiment |

Each graph includes a sentiment distribution chart in the header showing the emotional tone breakdown with counts and percentages.

### Tooltips

Hover over any edge to see:
- Relationship type and mention count
- Speaker attribution
- Up to 3 transcript quotes with temporal markers (early/middle/late)
- Sentiment label with emoji indicators

### Topic Browser

Click the floating **📚 Topics** button (bottom right) to open the topic sidebar. Each topic cluster shows keywords, episode count, and a list of episodes. Click a topic to filter the episode grid.

## Technical Details

### Pipeline Architecture

```
Transcripts (JSON)
    → spaCy NER (en_core_web_lg) → PERSON + PLACE entities
    → Context extraction (snippets, speakers, timestamps)
    → DistilBERT sentiment analysis per context
    → NetworkX directed graph construction
    → Temporal analysis (early/middle/late positioning)
    → BERTopic cross-episode clustering → topics.json
    → Per-episode + per-show + per-topic summary graphs
    → PyVis HTML visualization (with --visualize)
    → generate_index.py → index.json
```

### Dependencies

Defined in `pyproject.toml`, installed via `uv sync`:

- **spaCy** — Named entity recognition
- **NetworkX** — Graph construction and algorithms
- **PyVis** — Interactive HTML graph visualization
- **Transformers + PyTorch** — DistilBERT sentiment analysis
- **BERTopic + sentence-transformers** — Topic clustering
- **Polars** — Data processing
- **Rich** — Terminal output formatting
- **Click** — CLI interface

### Graph JSON Schema

Each `*_graph.json` contains:

```json
{
  "nodes": [
    { "id": "Donald Trump", "entity_type": "PERSON" }
  ],
  "edges": [
    {
      "source": "Donald Trump",
      "target": "Mar-a-Lago",
      "weight": 5,
      "relation": "mentioned_in",
      "travelers": [],
      "speakers": ["Rachel Maddow", "Guest"],
      "contexts": [
        {
          "text": "Trump was at Mar-a-Lago when...",
          "speaker": "Rachel Maddow",
          "position": "early",
          "sentiment": "NEGATIVE",
          "sentiment_score": 0.95,
          "timestamp": 42.5
        }
      ]
    }
  ]
}
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No episodes on landing page | `index.json` missing or stale | `uv run scripts/generate_index.py` |
| Topics sidebar empty | `graphs/topics.json` missing | Re-run pipeline with `--visualize` |
| Sentiment not in graph JSON | Old pipeline output | `--force --visualize` to regenerate |
| 404 warnings during model download | Normal — optional tokenizer files | Safe to ignore |
| Graphs blank in browser | `lib/` missing | Ensure `lib/vis-9.1.2/` exists |
| Deployment 413 error | File > 25 MB | Exclude large summary HTMLs from `site/` |

## Known Limitations

- Static site — no server-side filtering or dynamic data loading
- Graph files can be large for episodes with many entities (>25 MB summary graphs may exceed Cloudflare limits)
- BERTopic's hdbscan dependency emits `SyntaxWarning` about invalid escape sequences — harmless
- Single-file mode (`--input file.json --output out.json`) does not work reliably; use `--shows` instead

## License

This project is for personal/educational use.

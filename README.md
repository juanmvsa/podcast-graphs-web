# Podcast Conversation Graphs

Interactive network visualizations of entity relationships in podcast conversations. Extracts people and places from transcripts, analyzes sentiment, clusters episodes by topic, and generates interactive graph visualizations — all served as a static site on Cloudflare Pages.

## Quick Start

```bash
# 1. Install dependencies
uv sync
uv pip install en-core-web-lg@https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl

# 2. Generate graphs (all shows, with HTML visualizations)
uv run scripts/generate_entity_graphs.py --visualize

# 3. Preview locally
uv run python -m http.server 8000   # http://localhost:8000

# 4. Deploy to Cloudflare Pages
./scripts/deploy.sh
```

## Features

| Feature | Description |
|---------|-------------|
| 🌐 Interactive Graphs | Force-directed vis-network layouts with zoom, pan, drag |
| 😊 Sentiment Analysis | DistilBERT color-coded edges (green/red/gray) with distribution charts |
| 🏷️ Topic Clustering | BERTopic cross-episode clustering with sidebar topic browser |
| 💬 Rich Context | Hover tooltips show transcript quotes, speakers, temporal markers |
| 🔎 Search & Filter | Real-time search with combinable show/type/topic filters |
| 📱 Responsive | Desktop and mobile dark-theme UI |

## Project Structure

```
podcast-graphs-web/
├── index.html                     # Web app (Bootstrap 5 + vis-network)
├── index.json                     # Auto-generated catalog of all graphs
├── pyproject.toml                 # Python project config & dependencies
├── wrangler.toml                  # Cloudflare Pages deployment config
│
├── scripts/
│   ├── generate_entity_graphs.py  # Main pipeline: NER → graphs → sentiment → topics
│   ├── generate_index.py          # Scans graphs/ → writes index.json
│   ├── build_site.py              # Assembles site/ directory for deployment
│   ├── deploy.sh                  # Build + validate + deploy (single command)
│   ├── clean.sh                   # Removes caches and temp files
│   ├── validate_deployment.py     # Checks all files < 25 MB (Cloudflare limit)
│   └── utils/                     # Shared Rich logging utilities
│
├── graphs/                        # Generated output (one subdirectory per show)
│   ├── <show>/
│   │   ├── <episode>_graph.json   # Entity graph data (nodes, edges, sentiment, contexts)
│   │   ├── <episode>_graph.csv    # Adjacency matrix
│   │   └── <episode>_graph.html   # Interactive pyvis visualization
│   ├── summaries/
│   │   ├── <show>_graph.*         # Merged show-level summary
│   │   └── <show>/topic_*_graph.* # Per-topic summary graphs
│   └── topics.json                # Episode-to-topic cluster assignments
│
├── lib/                           # Frontend JS dependencies (vis-network, tom-select)
├── site/                          # Build output for deployment (gitignored, managed by build_site.py)
└── transcripts_.../               # Input: speaker-labeled JSON transcripts (one subdir per show)
```

## Pipeline

### How It Works

The pipeline in `generate_entity_graphs.py` processes podcast transcripts through these stages:

1. **Entity Extraction** — spaCy `en_core_web_lg` identifies PERSON and PLACE entities
2. **Global Normalization** — Two-pass approach: first collects all names across episodes, then normalizes variants (e.g., "Trump" → "Donald Trump")
3. **Graph Construction** — Builds directed networkx graphs: person→place movement edges and person↔person association edges, with speaker attribution
4. **Sentiment Analysis** — DistilBERT scores each edge context as positive/negative/neutral
5. **Topic Clustering** — BERTopic groups episodes by semantic similarity (requires ≥3 episodes)
6. **Visualization** — pyvis generates interactive HTML graphs; `generate_index.py` updates the web catalog

### CLI Reference

```
uv run scripts/generate_entity_graphs.py [OPTIONS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--shows <name>` | all shows | Process only specific shows (repeatable) |
| `--visualize` | off | Generate interactive HTML visualizations |
| `--force` | off | Reprocess episodes that already have output files |
| `--transcripts-dir <path>` | `transcripts_with_speaker_labels_postprocessed_with_utterance_and_document_labels` | Input directory |
| `--output-dir <path>` | `graphs` | Output directory |
| `--spacy-model <name>` | `en_core_web_lg` | spaCy NER model |
| `--log-level <level>` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `--input <file>` | — | Single-file mode (use `--shows` instead for reliability) |
| `--input-dir <dir>` | — | Recursively process all subdirectories as shows |

### Common Commands

```bash
# Generate graphs for a single show
uv run scripts/generate_entity_graphs.py --shows my_podcast --visualize

# Regenerate everything from scratch
uv run scripts/generate_entity_graphs.py --visualize --force

# Generate graphs without HTML (JSON + CSV only, much faster)
uv run scripts/generate_entity_graphs.py

# Regenerate only the web index (after manually editing graphs/)
uv run scripts/generate_index.py
```

### Output Files

| File | Created By | Contents |
|------|-----------|----------|
| `<episode>_graph.json` | generate_entity_graphs.py | Nodes, edges, adjacency matrix, sentiment, contexts |
| `<episode>_graph.csv` | generate_entity_graphs.py | Adjacency matrix in CSV format |
| `<episode>_graph.html` | generate_entity_graphs.py `--visualize` | Interactive pyvis visualization |
| `summaries/<show>_graph.*` | generate_entity_graphs.py | Merged graph across all episodes in a show |
| `summaries/<show>/topic_*_graph.*` | generate_entity_graphs.py `--visualize` | Per-topic summary graphs |
| `topics.json` | generate_entity_graphs.py | Topic cluster IDs, keywords, episode assignments |
| `index.json` | generate_index.py | Catalog of all shows, episodes, and topic summaries |

## Deployment

The site deploys to **Cloudflare Pages** as a static site. The `site/` directory is the publish root and is **gitignored** — it is rebuilt from scratch on every deploy.

### One-Command Deploy

```bash
# Generates graphs first, then builds and deploys
uv run scripts/generate_entity_graphs.py --visualize --force
./scripts/deploy.sh
```

### What `deploy.sh` Does

1. Clears `.wrangler/` and `__pycache__/` caches
2. Runs `build_site.py` — wipes `site/`, copies fresh `graphs/`, `lib/`, and `index.html`
3. Runs `generate_index.py --graphs-dir site/graphs --output site/index.json` — indexes the deployed graphs
4. Runs `validate_deployment.py` — ensures all files are under Cloudflare's 25 MB limit
5. Deploys `site/` via `npx wrangler pages deploy`

### Manual Deployment

```bash
# If you prefer to run each step individually:
uv run scripts/build_site.py
uv run scripts/generate_index.py --graphs-dir site/graphs --output site/index.json
uv run scripts/validate_deployment.py
npx wrangler pages deploy site --project-name=podcast-graphs-web
```

### Configuration

- **`wrangler.toml`** — project name and build output directory (`site`)
- **Cloudflare dashboard** — build settings are configured there, not in `wrangler.toml`
- **`.cfignore`** — files to exclude from Cloudflare deployment

## Development

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) — Python package manager
- Node.js (for `npx wrangler` deployment only)

### Setup

```bash
git clone <repo-url>
cd podcast-graphs-web
uv sync
uv pip install en-core-web-lg@https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl
```

> **Note:** `uv run python -m spacy download` does not work because uv's virtual environment does not include pip. Use the direct wheel URL above.

### Dependencies

Core libraries (see `pyproject.toml` for versions):

| Library | Purpose |
|---------|---------|
| spaCy + `en_core_web_lg` | Named entity recognition |
| networkx | Graph data structure and algorithms |
| pyvis | Interactive HTML graph generation |
| transformers + torch | DistilBERT sentiment analysis |
| BERTopic + sentence-transformers | Episode topic clustering |
| polars | Fast data manipulation |
| Rich + Click | CLI interface and logging |
| scikit-learn | ML utilities (used by BERTopic) |

### Local Preview

```bash
uv run python -m http.server 8000
# Open http://localhost:8000
```

The frontend loads `index.json` and `graphs/topics.json` on page load. All data is fetched client-side from static JSON files — no backend server required.

### Cleaning Up

```bash
# Remove caches and temp files
./scripts/clean.sh

# Or manually:
rm -rf .wrangler/ __pycache__/ site/
```

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `No module named pip` when installing spaCy model | uv doesn't bundle pip | Use `uv pip install en-core-web-lg@<wheel-url>` |
| Topics not showing in frontend | `topics.json` missing or empty | Re-run pipeline (needs ≥3 episodes per show for clustering) |
| Sentiment all neutral | Transformer model not downloaded | First run downloads DistilBERT automatically (~260 MB) |
| `SyntaxWarning: invalid escape sequence` | hdbscan dependency | Harmless warning, ignore |
| Deployment fails with file size error | HTML visualization > 25 MB | Remove large files or add to `.cfignore` |
| Episodes skipped on re-run | Output files already exist | Use `--force` to regenerate |
| Single-file mode (`--input`) behaves oddly | Known limitation | Use `--shows <name>` instead |
| Stale shows in deployed site | Old `site/` content | `deploy.sh` handles this — it rebuilds `site/` from scratch |

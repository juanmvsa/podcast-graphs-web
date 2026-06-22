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
| 🔍 Wikipedia Disambiguation | Automatic entity resolution via Wikipedia (caches results to disk) |
| 💬 Rich Context | Hover tooltips show transcript quotes, speakers, temporal position |
| 🔎 Search & Filter | Real-time search with combinable show/type/topic filters |
| 📱 Responsive | Desktop and mobile dark-theme UI |

## Project Structure

```
podcast-graphs-web/
├── index.html                     # Web app (Bootstrap 5 + vis-network)
├── index.json                     # Auto-generated catalog of all graphs
├── pyproject.toml                 # Python project config & dependencies
├── wrangler.toml                  # Cloudflare Pages deployment config
├── .cfignore                      # Cloudflare Pages deploy exclusions
│
├── scripts/
│   ├── generate_entity_graphs.py  # Thin CLI wrapper (delegates to podcast_graphs package)
│   ├── generate_index.py          # Scans graphs/ → writes index.json
│   ├── curate_topics.py           # Interactive topic label curation CLI
│   ├── build_site.py              # Assembles site/ directory for deployment
│   ├── deploy.sh                  # Build + validate + deploy (single command)
│   ├── clean.sh                   # Removes caches and temp files
│   ├── validate_deployment.py     # Checks all files < 25 MB (Cloudflare limit)
│   ├── utils/                     # Shared Rich logging utilities
│   │
│   └── podcast_graphs/            # Core Python package (modular pipeline)
│       ├── __init__.py
│       ├── types.py               # TypedDict, dataclass, and Enum definitions
│       ├── constants.py           # Regex patterns, stopwords, color constants
│       ├── sentiment.py           # DistilBERT sentiment analysis
│       ├── topics.py              # BERTopic clustering and curation
│       ├── pipeline.py            # Orchestration (episode processing, summaries)
│       ├── cli.py                 # Click CLI entry points
│       ├── entities/              # Named entity processing
│       │   ├── extraction.py      # spaCy NER extraction
│       │   ├── filtering.py       # Normalization, garbage detection, canonicalization
│       │   ├── resolution.py      # Partial name / abbreviation merging
│       │   └── wikipedia.py       # Wikipedia-based entity disambiguation
│       └── graph/                 # Graph construction and output
│           ├── construction.py    # Build episode graphs, merge across episodes
│           ├── serialization.py   # JSON/CSV serialization and I/O
│           └── visualization.py   # pyvis HTML generation (styles, scripts, legend)
│
├── graphs/                        # Generated output (one subdirectory per show)
│   ├── <show>/
│   │   ├── <episode>_graph.json   # Entity graph data (nodes, edges, sentiment, contexts)
│   │   ├── <episode>_graph.csv    # Adjacency matrix
│   │   └── <episode>_graph.html   # Interactive pyvis visualization
│   ├── summaries/
│   │   ├── <show>_graph.*         # Merged show-level summary
│   │   └── <show>/topic_*_graph.* # Per-topic summary graphs
│   ├── topics.json                # Episode-to-topic cluster assignments
│   └── .wiki_cache.json           # Wikipedia API response cache (gitignored)
│
├── lib/                           # Frontend JS dependencies (vis-network, tom-select)
├── site/                          # Build output for deployment (gitignored)
└── transcripts_.../               # Input: speaker-labeled JSON transcripts (one subdir per show)
```

## Pipeline

### Data Flow

```
Podcast Transcript (JSON)
        ↓
   [1] ENTITY EXTRACTION  (entities/extraction.py)
       spaCy en_core_web_lg identifies PERSON and PLACE entities
        ↓
   [2] ENTITY NORMALIZATION  (entities/filtering.py, resolution.py, wikipedia.py)
       Three-layer approach:
       • Partial name resolution — maps "Trump" → "Donald Trump"
       • Abbreviation merging — unifies "J.K. Rowling" / "J. K. Rowling"
       • Wikipedia disambiguation — resolves ambiguous names via API (cached)
        ↓
   [3] GRAPH CONSTRUCTION  (graph/construction.py)
       Directed NetworkX graphs: PERSON → PLACE "mentioned_in" edges
       Each edge carries speaker attribution, temporal position, transcript context
        ↓
   [4] SENTIMENT ANALYSIS  (sentiment.py)
       DistilBERT scores each edge context as POSITIVE / NEGATIVE / NEUTRAL
       Edges colored green / red / gray
        ↓
   [5] VISUALIZATION  (graph/visualization.py)
       pyvis generates interactive HTML with custom CSS/JS legend
        ↓
   [6] SHOW AGGREGATION  (pipeline.py)
       Merge individual episode graphs into show-level summaries
        ↓
   [7] TOPIC CLUSTERING  (topics.py)
       BERTopic groups episodes by semantic similarity (≥3 episodes required)
       Generates per-topic summary graphs
        ↓
   [8] INDEX GENERATION  (generate_index.py)
       Scans graphs/ → writes index.json for the web frontend

OUTPUT FILES
├── graphs/<show>/<episode>_graph.html     (interactive visualization)
├── graphs/<show>/<episode>_graph.json     (serialized graph data)
├── graphs/<show>/<episode>_graph.csv      (adjacency matrix)
├── graphs/summaries/<show>_graph.html     (show-level summary)
├── graphs/summaries/<show>/topic_*_graph.*(per-topic summary)
├── graphs/topics.json                     (topic clustering results)
├── graphs/topic_labels.json               (human curations)
├── graphs/.wiki_cache.json                (Wikipedia cache)
└── index.json                             (web app catalog)
```

### Two-Pass Processing

The pipeline uses a two-pass strategy for global entity consistency:

1. **Pass 1 — Collect**: Scan all episodes in a show to extract raw entity sets
2. **Build global resolution maps**: Merge partial names, abbreviations, and Wikipedia lookups across the entire show
3. **Pass 2 — Process**: Re-process each episode applying the global maps, ensuring "Sam" always resolves to "Sam Altman" show-wide

### Edge Labeling Pipeline

Edges represent the relationship between a **PERSON** entity and a **PLACE** entity that co-occur within the same transcript segment. The full lifecycle of an edge is:

#### 1. Creation (`graph/construction.py` → `_add_or_update_association_edge()`)

For each transcript segment, the pipeline identifies which persons are "active" (mentioned in the segment or currently speaking) and which places appear. It then creates a directed edge for every `(person, place)` pair:

```python
graph.add_edge(person, place,
    weight=1,
    relation="mentioned_in",
    contexts=[{
        "text":      "<segment text>",
        "speaker":   "<speaker id>",
        "temporal":  "early" | "middle" | "late",
        "timestamp": <float seconds>,
        "sentiment": {"label": "...", "score": 0.0, "emoji": "..."}
    }],
    speakers=["<speaker id>"],
)
```

If the same `(person, place)` pair appears in multiple segments, the edge's `weight` is incremented and new context entries are appended (capped at `MAX_CONTEXTS_PER_EDGE = 3`).

#### 2. Sentiment Scoring (`sentiment.py` → `analyze_sentiment()`)

Each context snippet is scored independently using **DistilBERT** (`distilbert-base-uncased-finetuned-sst-2-english`). The model classifies the first 512 tokens of the segment text as:

| Label | Emoji | Meaning |
|-------|-------|---------|
| `POSITIVE` | 😊 | Favorable or optimistic tone |
| `NEGATIVE` | 😞 | Critical or pessimistic tone |
| `NEUTRAL` | 😐 | Balanced or factual tone |

The sentiment result (`label`, `score`, `emoji`) is stored inside each context entry on the edge.

#### 3. Edge Constraints

Edges are constrained **by design** at the construction level — no post-hoc filtering is needed:

- **PERSON → PLACE** — the only allowed edge type. Created when a person and place co-occur in a segment.
- **PLACE → PLACE** — impossible. The inner loop only pairs persons with places; places are never added to the `active_persons` set.
- **PERSON → PERSON** — not generated. People may co-occur in the same segment, but no edges are created between them.
- **Entity overlap** — if a token appears as both PERSON and PLACE during extraction, it is removed from the PLACE set (`extraction.py`, line ~138), so PERSON always takes priority.

#### 4. Merging (`graph/construction.py` → `merge_graphs()`)

When individual episode graphs are merged into show-level or topic-level summaries:

- Edge **weights are summed** across episodes
- **Speaker lists are deduplicated** (union of all speakers)
- **Contexts are capped** at `MAX_CONTEXTS_MERGED = 5` (keeping the most diverse set)
- The `relation` field remains `"mentioned_in"`

#### 5. Visualization (`graph/visualization.py` → `visualize_graph()`)

Edges are rendered in the interactive HTML visualization with:

- **Color** determined by **dominant sentiment** (majority vote across all contexts on that edge):
  - 🟢 Green = POSITIVE
  - 🔴 Red = NEGATIVE
  - ⚫ Gray = NEUTRAL
- **Width** proportional to `weight` (number of co-occurrence mentions)
- **Rich tooltip** on hover showing:
  - `📍 PERSON → PLACE`
  - `Relationship: Mentioned In`
  - `Mentions: <weight>`
  - `Overall Sentiment: <label> <emoji>`
  - `Discussed by: <unique speakers>`
  - `💬 Context:` up to 2 representative snippets with temporal label (🕐 Early / 🕑 Mid / 🕒 Late), sentiment emoji, speaker, and truncated text

#### Edge Data Schema

The complete edge object as serialized to JSON:

```json
{
  "source": "Donald Trump",
  "target": "White House",
  "weight": 5,
  "relation": "mentioned_in",
  "speakers": ["speaker_01", "speaker_03"],
  "contexts": [
    {
      "text": "The president returned to the White House after...",
      "speaker": "speaker_01",
      "temporal": "early",
      "timestamp": 142.5,
      "sentiment": {
        "label": "POSITIVE",
        "score": 0.987,
        "emoji": "😊"
      }
    }
  ]
}
```

## CLI Reference

### `generate_entity_graphs.py`

```bash
uv run scripts/generate_entity_graphs.py [OPTIONS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--shows <name>` | all shows | Process only specific shows (repeatable) |
| `--visualize` | off | Generate interactive HTML visualizations |
| `--force` | off | Reprocess episodes that already have output files |
| `--transcripts-dir <path>` | `transcripts_with_speaker_labels_...` | Input directory |
| `--output-dir <path>` | `graphs` | Output directory |
| `--spacy-model <name>` | `en_core_web_lg` | spaCy NER model |
| `--log-level <level>` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `-i, --input <file>` | — | Single-file mode |
| `-d, --input-dir <dir>` | — | Recursively process all subdirectories as shows |
| `-o, --output <file>` | — | Output file path (single-file mode only) |

### `generate_index.py`

```bash
uv run scripts/generate_index.py [--graphs-dir <path>] [--output <path>]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--graphs-dir` | `graphs` | Directory to scan for graph files |
| `--output` | `index.json` | Output path for the generated index |

### `curate_topics.py`

```bash
uv run scripts/curate_topics.py [--topics-file <path>] [--labels-file <path>]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--topics-file` | `graphs/topics.json` | Path to topics.json from the pipeline |
| `--labels-file` | same dir as topics-file | Path to save/load topic_labels.json |

### Common Commands

```bash
# Generate graphs for a single show
uv run scripts/generate_entity_graphs.py --shows my_podcast --visualize

# Regenerate everything from scratch
uv run scripts/generate_entity_graphs.py --visualize --force

# Generate graphs without HTML (JSON + CSV only, much faster)
uv run scripts/generate_entity_graphs.py

# Process a single transcript file
uv run scripts/generate_entity_graphs.py -i transcripts_*/my_show/episode.json -o /tmp/out.json

# Regenerate only the web index (after manually editing graphs/)
uv run scripts/generate_index.py

# Clean all caches and temp files
./scripts/clean.sh
```

### Topic Curation

The pipeline auto-generates topic labels using BERTopic with KeyBERT-inspired representations. Topics are meaningful out of the box (e.g., "transgender, trans kids, lgbt"), but you can assign human-readable labels for a polished frontend experience.

```bash
# 1. Generate graphs (topics.json is created automatically)
uv run scripts/generate_entity_graphs.py --shows my_podcast --visualize

# 2. Interactively review and label each topic
uv run scripts/curate_topics.py

# 3. Re-run the pipeline — curated labels are applied automatically
uv run scripts/generate_entity_graphs.py --shows my_podcast --visualize --force
```

The curation tool presents each topic with its top words, representative episodes, and sample excerpts. For each topic you can:
- **Assign a label** — e.g., "Trans Rights & LGBTQ+ Identity"
- **Discard** — hide the topic from the frontend (`d`)
- **Merge** — combine into another topic (`m<id>`)

Curated labels are saved to `graphs/topic_labels.json` and automatically applied on subsequent pipeline runs. The frontend prefers curated labels when available.

> **Note:** If you re-run the pipeline and topic IDs change (e.g., different number of episodes), you'll see warnings about stale references in `topic_labels.json`. Re-run `curate_topics.py` to update.

## Package Architecture

The core logic lives in `scripts/podcast_graphs/`, a modular Python package with a robust type system.

### Type System

| Type | Kind | Purpose |
|------|------|---------|
| `EntityType` | `Enum` | `PERSON`, `PLACE` |
| `SentimentLabel` | `Enum` | `POSITIVE`, `NEGATIVE`, `NEUTRAL` |
| `TemporalPosition` | `Enum` | `EARLY`, `MIDDLE`, `LATE` |
| `EntityResult` | `dataclass` | Per-episode extraction output (persons, places, segment_entities) |
| `ResolutionMaps` | `dataclass` | Show-wide name resolution maps and blocklists |
| `EpisodeGraphData` | `dataclass` | Serialized episode graph (nodes, edges, adjacency matrix) |
| `ShowGraphData` | `dataclass` | Serialized show summary graph |
| `TranscriptSegment` | `TypedDict` | Input transcript JSON shape |
| `SegmentEntities` | `TypedDict` | Per-segment entity associations |
| `ContextEntry` | `TypedDict` | Edge context (text, sentiment, speaker, temporal) |
| `SentimentResult` | `TypedDict` | Sentiment analysis output |
| `SerializedEdge` | `TypedDict` | JSON-serializable edge data |
| `TopicResults` | `TypedDict` | Topic clustering output |
| `TopicCurations` | `TypedDict` | Human-curated topic labels |

### Module Responsibilities

| Module | Lines | Responsibility |
|--------|-------|---------------|
| `types.py` | ~240 | All type definitions (`TypedDict`, `dataclass`, `Enum`) |
| `constants.py` | ~270 | Regex patterns, stopword `frozenset`s, color constants, abbreviation tables |
| `entities/extraction.py` | ~155 | spaCy NER extraction with `nlp.pipe()` batching |
| `entities/filtering.py` | ~130 | Normalization, garbage detection, canonicalization |
| `entities/resolution.py` | ~115 | Partial-name and abbreviation merging across episodes |
| `entities/wikipedia.py` | ~165 | Wikipedia API disambiguation with persistent JSON cache |
| `graph/construction.py` | ~150 | Episode graph building and cross-episode merging |
| `graph/serialization.py` | ~100 | JSON/CSV output and adjacency matrix generation |
| `graph/visualization.py` | ~1090 | pyvis HTML generation with custom CSS, JS, and legend |
| `sentiment.py` | ~55 | Lazy-loaded DistilBERT sentiment classification |
| `topics.py` | ~230 | BERTopic clustering, diversity metrics, curated label application |
| `pipeline.py` | ~400 | Orchestration: episode processing, show summaries, index generation |
| `cli.py` | ~440 | Click CLI commands, argument parsing, input mode routing |

### Design Patterns

- **Lazy model loading** — spaCy, DistilBERT, and sentence-transformers are loaded only when needed. CLI startup is fast.
- **Immutable constants** — All stopword sets use `frozenset` to prevent accidental mutation.
- **Two-pass processing** — Global entity resolution maps are built in pass 1, applied in pass 2.
- **Persistent caching** — Wikipedia API responses are cached to `.wiki_cache.json` across runs.
- **Sentiment-aware edges** — Every edge carries context snippets with sentiment, speaker, temporal position, and original text.

## Deployment

The site deploys to **Cloudflare Pages** as a static site. The `site/` directory is the publish root and is **gitignored** — it is rebuilt from scratch on every deploy.

### One-Command Deploy

```bash
# Generate graphs first, then build and deploy
uv run scripts/generate_entity_graphs.py --visualize --force
./scripts/deploy.sh
```

### What `deploy.sh` Does

1. Clears `.wrangler/` and `__pycache__/` caches
2. Runs `uv run scripts/build_site.py` — wipes `site/`, copies fresh `graphs/`, `lib/`, and `index.html` (auto-excludes files > 25 MB)
3. Runs `uv run scripts/generate_index.py --graphs-dir site/graphs --output site/index.json`
4. Runs `uv run scripts/validate_deployment.py` — ensures all files are under Cloudflare's 25 MB limit
5. Deploys `site/` via `npx wrangler pages deploy`

### Manual Deployment

```bash
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
| wikipedia-api | Entity disambiguation via Wikipedia |
| polars | Fast data manipulation |
| Rich + Click | CLI interface and logging |
| scikit-learn | ML utilities (used by BERTopic) |

### Linting

```bash
uv run ruff check scripts/podcast_graphs/    # lint
uv run ruff check scripts/podcast_graphs/ --fix  # auto-fix
uv run mypy scripts/podcast_graphs/          # type checking (strict mode)
```

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
| Deployment fails with file size error | File > 25 MB in `site/` | `build_site.py` auto-excludes these; check with `validate_deployment.py` |
| Episodes skipped on re-run | Output files already exist | Use `--force` to regenerate |
| Wikipedia queries are slow on first run | No cache exists yet | Subsequent runs use `.wiki_cache.json` and are instant |
| Stale topic labels after re-run | Topic IDs changed between runs | Re-run `uv run scripts/curate_topics.py` to update curations |
| Stale shows in deployed site | Old `site/` content | `deploy.sh` handles this — it rebuilds `site/` from scratch |

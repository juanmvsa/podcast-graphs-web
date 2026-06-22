# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Code Style

- Always use `uv run` to execute Python commands, never bare `python3` or `python`.
- Always provide modular, clean, and typed code with comments explaining purpose and type annotations.
- Always write comments in lowercase and end them with a period.

## Common Commands

```bash
# install dependencies (one-time setup).
uv sync
uv pip install en-core-web-lg@https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl

# generate graphs for all shows with visualizations.
uv run scripts/generate_entity_graphs.py --visualize

# generate graphs for a single show.
uv run scripts/generate_entity_graphs.py --shows my_podcast --visualize

# regenerate everything from scratch.
uv run scripts/generate_entity_graphs.py --visualize --force

# process a single transcript file.
uv run scripts/generate_entity_graphs.py -i transcripts_*/my_show/episode.json -o /tmp/out.json

# regenerate web index only.
uv run scripts/generate_index.py

# interactively curate topic labels.
uv run scripts/curate_topics.py

# local preview.
uv run python -m http.server 8000

# deploy to cloudflare pages.
./scripts/deploy.sh

# clean caches and temp files.
./scripts/clean.sh

# linting and type checking.
uv run ruff check scripts/podcast_graphs/
uv run ruff check scripts/podcast_graphs/ --fix
uv run mypy scripts/podcast_graphs/

# run tests.
uv run pytest tests/
```

## Architecture

This is a static site generator that processes podcast transcripts into interactive network visualizations deployed to Cloudflare Pages.

### Data Flow Pipeline

```
Transcript JSON → Entity Extraction (spaCy) → Entity Normalization → Graph Construction (NetworkX)
    → Sentiment Analysis (DistilBERT) → HTML Visualization (pyvis) → Show/Topic Summaries → Index Generation
```

### Two-Pass Processing

The pipeline uses two passes for global entity consistency:
1. **Pass 1 (Collect)**: Scan all episodes to extract raw entity sets.
2. **Build global resolution maps**: Merge partial names, abbreviations, Wikipedia lookups across the show.
3. **Pass 2 (Process)**: Re-process each episode applying global maps (e.g., "Sam" → "Sam Altman" show-wide).

### Core Package Structure (`scripts/podcast_graphs/`)

| Module | Purpose |
|--------|---------|
| `types.py` | TypedDict, dataclass, and Enum definitions |
| `constants.py` | Regex patterns, stopwords, color constants |
| `entities/extraction.py` | spaCy NER extraction with batched `nlp.pipe()` |
| `entities/filtering.py` | Normalization, garbage detection, canonicalization |
| `entities/resolution.py` | Partial-name and abbreviation merging |
| `entities/wikipedia.py` | Wikipedia API disambiguation with JSON cache |
| `graph/construction.py` | Episode graph building and cross-episode merging |
| `graph/serialization.py` | JSON/CSV output and adjacency matrices |
| `graph/visualization.py` | pyvis HTML generation with custom CSS/JS |
| `sentiment.py` | Lazy-loaded DistilBERT sentiment classification |
| `topics.py` | BERTopic clustering and curated label application |
| `pipeline.py` | Orchestration: episode processing, summaries, index |
| `cli.py` | Click CLI commands and argument parsing |

### Key Design Patterns

- **Lazy model loading**: spaCy, DistilBERT, and sentence-transformers load only when needed.
- **Immutable constants**: All stopword sets use `frozenset`.
- **Persistent caching**: Wikipedia API responses cache to `graphs/.wiki_cache.json`.
- **Sentiment-aware edges**: Edges carry context snippets with sentiment, speaker, temporal position.

### Edge Constraints

- Only **PERSON → PLACE** edges are created (co-occurrence in same segment).
- PERSON always takes priority if a token appears as both PERSON and PLACE.
- No PLACE → PLACE or PERSON → PERSON edges.

### Output Structure

```
graphs/
├── <show>/<episode>_graph.{json,csv,html}   # per-episode graphs
├── summaries/<show>_graph.{json,csv,html}   # show-level summary
├── summaries/<show>/topic_*_graph.*         # per-topic summaries
├── topics.json                               # episode-to-topic assignments
├── topic_labels.json                         # human curations
└── .wiki_cache.json                          # wikipedia cache (gitignored)

site/                                         # build output (gitignored)
index.json                                    # web app catalog
```

### Deployment

The `site/` directory is rebuilt from scratch on each deploy. Files > 25 MB are auto-excluded (Cloudflare limit). Use `./scripts/deploy.sh` for full build + validate + deploy.

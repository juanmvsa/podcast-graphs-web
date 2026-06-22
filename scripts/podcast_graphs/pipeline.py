"""Pipeline orchestration: entity collection, resolution, and episode processing.

Coordinates the full pipeline: raw entity collection, global resolution map
construction, episode processing, show aggregation, topic clustering,
and per-topic summary generation.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import networkx as nx
from pydantic import ValidationError

from podcast_graphs.constants import AMBIGUOUS_GEO_NAMES
from podcast_graphs.entities.extraction import (
    extract_entities_from_doc,
    extract_episode_entities,
)
from podcast_graphs.entities.resolution import (
    apply_name_resolution,
    close_resolution_map,
    resolve_abbreviation_variants,
    resolve_partial_names,
    resolve_place_duplicates,
)
from podcast_graphs.entities.wikipedia import resolve_persons_via_wikipedia
from podcast_graphs.graph.construction import build_episode_graph, merge_graphs
from podcast_graphs.graph.serialization import (
    graph_to_adjacency_matrix,
    save_adjacency_csv,
    save_graph_data,
    serialize_edges,
    serialize_graph,
)
from podcast_graphs.graph.visualization import humanize_title, visualize_graph
from podcast_graphs.topics import compute_topic_diversity
from podcast_graphs.types import (
    EpisodeGraphData,
    ResolutionMaps,
    ShowGraphData,
    TranscriptSegment,
)

if TYPE_CHECKING:
    import spacy
    from rich.progress import Progress

logger = logging.getLogger(__name__)


def collect_raw_entities(
    nlp: spacy.Language,
    episode_files: list[Path],
    progress: Progress | None = None,
    task_id: int | None = None,
) -> tuple[set[str], set[str]]:
    """First pass: collect all raw entities across all episodes in a show.

    Uses nlp.pipe() for batched inference per episode.
    Returns aggregated person and place entity sets before cross-episode
    normalization.
    """
    from podcast_graphs.constants import NLP_PIPE_BATCH_SIZE

    all_persons: set[str] = set()
    all_places: set[str] = set()

    for episode_file in episode_files:
        try:
            with open(episode_file, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            if progress and task_id is not None:
                progress.advance(task_id)
            continue

        texts = [
            seg.get("text", "")
            for seg in data.get("segments", [])
            if seg.get("text", "").strip()
        ]

        for doc in nlp.pipe(texts, batch_size=NLP_PIPE_BATCH_SIZE):
            persons, places = extract_entities_from_doc(doc)
            all_persons.update(persons)
            all_places.update(places)

        if progress and task_id is not None:
            progress.advance(task_id)

    return all_persons, all_places


def build_global_resolution_maps(
    all_persons: set[str],
    all_places: set[str],
) -> ResolutionMaps:
    """Build show-level entity resolution maps and blocklists.

    Returns a ResolutionMaps containing person/place resolution dicts
    and blocklists. These normalize entities consistently across all
    episodes in a show.
    """
    # resolve partial names globally
    person_partial = resolve_partial_names(all_persons)
    person_abbrev = resolve_abbreviation_variants(all_persons)
    person_resolution = {**person_abbrev, **person_partial}

    # Wikipedia-based disambiguation
    wiki_resolution = resolve_persons_via_wikipedia(all_persons, person_resolution)
    person_resolution = {**person_resolution, **wiki_resolution}

    # close transitive chains
    person_resolution = close_resolution_map(person_resolution)

    place_dupes = resolve_place_duplicates(all_places)
    cleaned_places = apply_name_resolution(all_places, place_dupes)
    place_partial = resolve_partial_names(cleaned_places)
    place_abbrev = resolve_abbreviation_variants(cleaned_places)
    place_resolution = {**place_dupes, **place_abbrev, **place_partial}

    # resolve all names first, then detect cross-entity overlap
    resolved_persons = apply_name_resolution(all_persons, person_resolution)
    resolved_places = apply_name_resolution(all_places, place_resolution)

    # entities that appear as both PERSON and PLACE get blocked from places
    overlap = resolved_persons & resolved_places
    place_blocklist = overlap.copy()

    # also block places that share a name token with a known person
    person_full_names = {p for p in resolved_persons if len(p.split()) >= 2}
    person_name_tokens: dict[str, list[str]] = {}
    for person in person_full_names:
        for token in person.split():
            person_name_tokens.setdefault(token, []).append(person)

    for place in list(resolved_places):
        place_tokens = place.split()
        if len(place_tokens) <= 2:
            for person in person_full_names:
                if place == person:
                    place_blocklist.add(place)
                    break
            if len(place_tokens) == 1 and place in person_name_tokens:
                if place not in AMBIGUOUS_GEO_NAMES:
                    place_blocklist.add(place)

    person_blocklist: set[str] = set()

    return ResolutionMaps(
        person_resolution=person_resolution,
        place_resolution=place_resolution,
        person_blocklist=person_blocklist,
        place_blocklist=place_blocklist,
    )


def process_episode(
    nlp: spacy.Language,
    transcript_path: Path,
    show_name: str,
    global_person_resolution: dict[str, str] | None = None,
    global_place_resolution: dict[str, str] | None = None,
    global_person_blocklist: set[str] | None = None,
    global_place_blocklist: set[str] | None = None,
) -> tuple[EpisodeGraphData, nx.DiGraph] | None:
    """Process a single episode transcript and return graph data."""
    try:
        with open(transcript_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.error("failed to read %s: %s", transcript_path, e)
        return None

    raw_segments = data.get("segments", [])
    if not raw_segments:
        logger.warning("no segments in %s", transcript_path.name)
        return None

    # validate raw transcript dicts into typed models, skipping malformed ones
    # (empty text, end <= start, etc.) rather than crashing the whole episode.
    segments: list[TranscriptSegment] = []
    for raw in raw_segments:
        try:
            segments.append(TranscriptSegment(**raw))
        except (ValidationError, TypeError) as e:
            logger.warning("skipping invalid segment in %s: %s", transcript_path.name, e)
    if not segments:
        logger.warning("no valid segments in %s", transcript_path.name)
        return None

    episode_name = transcript_path.stem

    entity_result = extract_episode_entities(
        nlp,
        segments,
        global_person_resolution=global_person_resolution,
        global_place_resolution=global_place_resolution,
        global_person_blocklist=global_person_blocklist,
        global_place_blocklist=global_place_blocklist,
    )
    graph = build_episode_graph(entity_result)
    graph_data = serialize_graph(graph, episode_name, show_name, entity_result)
    return graph_data, graph


def generate_per_topic_summaries(
    topic_results: dict[str, object],
    all_episode_graphs: dict[str, dict[str, object]],
    output_dir: Path,
    visualize: bool = True,
    topics_per_graph: int = 3,
) -> None:
    """Generate summary graphs grouped by topics."""
    from utils.rich_utils import console

    topics = topic_results.get("topics", [])
    episode_topics = topic_results.get("episode_topics", {})

    if not topics or not all_episode_graphs:
        return

    console.print("\n[bold cyan]Generating per-topic summary graphs...[/bold cyan]")

    # group episodes by show and topic
    show_topic_episodes: dict[str, dict[int, list[str]]] = {}

    for episode_name, topic_data in episode_topics.items():
        if episode_name not in all_episode_graphs:
            continue
        show_name = all_episode_graphs[episode_name]["show"]
        topic_id = topic_data["topic_id"]
        if show_name not in show_topic_episodes:
            show_topic_episodes[show_name] = {}
        if topic_id not in show_topic_episodes[show_name]:
            show_topic_episodes[show_name][topic_id] = []
        show_topic_episodes[show_name][topic_id].append(episode_name)

    for show_name, topic_episodes in show_topic_episodes.items():
        show_summaries_dir = output_dir / "summaries" / show_name
        show_summaries_dir.mkdir(parents=True, exist_ok=True)

        sorted_topics = sorted(
            topic_episodes.items(), key=lambda x: len(x[1]), reverse=True
        )

        # group topics into batches
        topic_batches: list[tuple[list[int], list[str]]] = []
        current_batch: list[str] = []
        current_batch_topics: list[int] = []

        for topic_id, episodes in sorted_topics:
            current_batch.extend(episodes)
            current_batch_topics.append(topic_id)
            if len(current_batch_topics) >= topics_per_graph:
                topic_batches.append((current_batch_topics, current_batch))
                current_batch = []
                current_batch_topics = []

        if current_batch_topics:
            topic_batches.append((current_batch_topics, current_batch))

        for batch_idx, (batch_topic_ids, batch_episodes) in enumerate(topic_batches):
            batch_graphs = [
                all_episode_graphs[ep]["graph"]
                for ep in batch_episodes
                if ep in all_episode_graphs
            ]
            if not batch_graphs:
                continue

            merged = merge_graphs(batch_graphs)
            if merged.number_of_nodes() == 0:
                continue

            # get topic labels
            topic_labels = []
            for tid in batch_topic_ids:
                topic_info = next(
                    (t for t in topics if t["topic_id"] == tid), None
                )
                if topic_info:
                    topic_labels.append(topic_info["topic_label"])

            if len(batch_topic_ids) == 1:
                filename = f"topic_{batch_topic_ids[0]}_graph"
                subtitle = f"Topic: {topic_labels[0]} ({len(batch_episodes)} episodes)"
            else:
                topic_ids_str = "_".join(map(str, batch_topic_ids))
                filename = f"topics_{topic_ids_str}_graph"
                subtitle = f"Topics {batch_idx + 1}: {len(batch_episodes)} episodes"

            nodes, matrix = graph_to_adjacency_matrix(merged)
            edges = serialize_edges(merged)

            summary_data = ShowGraphData(
                show=show_name,
                episode_count=len(batch_episodes),
                persons=sorted(
                    n
                    for n in merged.nodes()
                    if merged.nodes[n].get("entity_type") == "PERSON"
                ),
                places=sorted(
                    n
                    for n in merged.nodes()
                    if merged.nodes[n].get("entity_type") == "PLACE"
                ),
                nodes=nodes,
                adjacency_matrix=matrix,
                edges=edges,
            )

            json_path = show_summaries_dir / f"{filename}.json"
            save_graph_data(summary_data, json_path)
            save_adjacency_csv(merged, show_summaries_dir / filename)

            if visualize:
                html_path = show_summaries_dir / f"{filename}.html"
                visualize_graph(
                    merged,
                    html_path,
                    title=humanize_title(show_name),
                    subtitle=subtitle,
                )

            logger.info(
                "  Generated topic summary: %s/%s (%d nodes, %d edges)",
                show_name,
                filename,
                merged.number_of_nodes(),
                merged.number_of_edges(),
            )

    console.print(
        f"[bold green]\u2713[/bold green] Generated per-topic summaries for "
        f"{len(show_topic_episodes)} shows"
    )


def apply_topic_curations(
    topic_results: dict[str, object],
    labels_path: Path,
) -> None:
    """Apply curated labels, merges, and discards from topic_labels.json.

    Modifies topic_results in-place.
    """
    from utils.rich_utils import console

    try:
        with labels_path.open() as f:
            curations = json.load(f)

        curated_labels: dict[str, str] = {
            str(k): v for k, v in curations.get("labels", {}).items()
        }
        discarded_ids: set[int] = {int(x) for x in curations.get("discarded", [])}
        merge_map: dict[int, int] = {
            int(k): int(v) for k, v in curations.get("merged", {}).items()
        }

        # validate: warn about stale references
        current_topic_ids = {t["topic_id"] for t in topic_results.get("topics", [])}
        for tid_str in curated_labels:
            if int(tid_str) not in current_topic_ids:
                logger.warning(
                    "topic_labels.json references topic %s which doesn't exist", tid_str
                )
        for did in discarded_ids:
            if did not in current_topic_ids:
                logger.warning(
                    "topic_labels.json discards topic %d which doesn't exist", did
                )

        # apply curated labels
        for topic in topic_results.get("topics", []):
            tid = str(topic["topic_id"])
            if tid in curated_labels:
                topic["curated_label"] = curated_labels[tid]

        # apply merges and labels to episode_topics
        for ep_data in topic_results.get("episode_topics", {}).values():
            orig_id = ep_data["topic_id"]
            if orig_id in merge_map:
                ep_data["topic_id"] = merge_map[orig_id]
            tid = str(ep_data["topic_id"])
            if tid in curated_labels:
                ep_data["curated_label"] = curated_labels[tid]

        # remove discarded topics and merged-away source topics from the summary
        # list (their episodes were reassigned to the merge target above).
        merged_sources = set(merge_map.keys())
        topic_results["topics"] = [
            t
            for t in topic_results["topics"]
            if t["topic_id"] not in discarded_ids
            and t["topic_id"] not in merged_sources
        ]
        topic_results["episode_topics"] = {
            ep: data
            for ep, data in topic_results.get("episode_topics", {}).items()
            if data["topic_id"] not in discarded_ids
        }

        # recompute each surviving topic's episode membership from the remapped
        # episode_topics so merge targets pick up their merged-in episodes.
        episodes_by_topic: dict[int, list[str]] = {}
        for ep, data in topic_results["episode_topics"].items():
            episodes_by_topic.setdefault(data["topic_id"], []).append(ep)
        for topic in topic_results["topics"]:
            members = episodes_by_topic.get(topic["topic_id"], [])
            topic["episodes"] = members
            topic["episode_count"] = len(members)

        # recalculate metrics
        updated_diversity = compute_topic_diversity(topic_results.get("topics", []))
        metrics = topic_results.setdefault("metrics", {})
        metrics["num_topics"] = len(topic_results.get("topics", []))
        metrics["topic_diversity"] = round(updated_diversity, 3)

        console.print(
            f"[dim]Applied curated labels from {labels_path} "
            f"({len(curated_labels)} labels, {len(discarded_ids)} discarded, "
            f"{len(merge_map)} merged)[/dim]"
        )
    except Exception as e:
        console.print(
            f"[bold yellow]Warning: Could not apply topic_labels.json: {e}[/bold yellow]"
        )

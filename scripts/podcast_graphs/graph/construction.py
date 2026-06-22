"""Graph construction and merging.

Builds directed graphs from entity extraction results and merges
per-episode graphs into show-level aggregated graphs.
"""

from __future__ import annotations

import networkx as nx

from podcast_graphs.constants import (
    EARLY_THRESHOLD,
    LATE_THRESHOLD,
    MAX_CONTEXTS_MERGED,
    MAX_CONTEXTS_PER_EDGE,
)
from podcast_graphs.entities.filtering import normalize_entity
from podcast_graphs.sentiment import analyze_sentiment
from podcast_graphs.types import EntityResult


def _add_or_update_association_edge(
    graph: nx.DiGraph,
    person: str,
    place: str,
    text: str,
    speaker: str,
    temporal: str,
    timestamp: float,
) -> None:
    """Add or update a person → place 'mentioned_in' edge."""
    if graph.has_edge(person, place):
        edge_data = graph[person][place]
        edge_data["weight"] += 1
        if len(edge_data.get("contexts", [])) < MAX_CONTEXTS_PER_EDGE:
            sentiment = analyze_sentiment(text)
            edge_data.setdefault("contexts", []).append({
                "text": text,
                "speaker": speaker,
                "temporal": temporal,
                "timestamp": timestamp,
                "sentiment": sentiment,
            })
        if speaker and speaker not in edge_data.get("speakers", []):
            edge_data.setdefault("speakers", []).append(speaker)
    else:
        sentiment = analyze_sentiment(text)
        graph.add_edge(
            person,
            place,
            weight=1,
            relation="mentioned_in",
            contexts=[{
                "text": text,
                "speaker": speaker,
                "temporal": temporal,
                "timestamp": timestamp,
                "sentiment": sentiment,
            }],
            speakers=[speaker] if speaker else [],
        )


def build_episode_graph(entity_result: EntityResult) -> nx.DiGraph:
    """Build a directed graph from episode entity data.

    Creates PERSON → PLACE edges when a person is discussed in connection
    with a place. Edges carry sentiment, speaker, temporal position, and
    transcript context.
    """
    graph = nx.DiGraph()

    for person in entity_result.persons:
        graph.add_node(person, entity_type="PERSON")
    for place in entity_result.places:
        graph.add_node(place, entity_type="PLACE")

    total_segments = len(entity_result.segment_entities)

    for seg_ents in entity_result.segment_entities:
        persons_in_seg = seg_ents["persons"]
        places_in_seg = seg_ents["places"]
        speaker = seg_ents.get("speaker_name") or seg_ents.get("speaker", "")
        text = seg_ents.get("text", "")
        seg_idx = seg_ents.get("segment_index", 0)
        timestamp = seg_ents.get("timestamp", 0)

        # calculate temporal position
        position_pct = (seg_idx / total_segments) * 100 if total_segments > 0 else 0
        if position_pct < EARLY_THRESHOLD:
            temporal = "early"
        elif position_pct < LATE_THRESHOLD:
            temporal = "middle"
        else:
            temporal = "late"

        if not places_in_seg:
            continue

        if persons_in_seg:
            active_persons = persons_in_seg
        else:
            speaker_name = seg_ents.get("speaker_name") or seg_ents.get("speaker", "")
            if not speaker_name:
                continue
            speaker_normalized = normalize_entity(speaker_name)
            if not graph.has_node(speaker_normalized):
                graph.add_node(speaker_normalized, entity_type="PERSON")
            active_persons = [speaker_normalized]

        for person in active_persons:
            for place in places_in_seg:
                _add_or_update_association_edge(
                    graph, person, place, text, speaker, temporal, timestamp
                )

    return graph


def merge_graphs(graphs: list[nx.DiGraph]) -> nx.DiGraph:
    """Merge multiple directed graphs into a single aggregated graph."""
    merged = nx.DiGraph()
    for g in graphs:
        for node, attrs in g.nodes(data=True):
            if not merged.has_node(node):
                merged.add_node(node, **attrs)
        for u, v, data in g.edges(data=True):
            if merged.has_edge(u, v):
                merged[u][v]["weight"] = (
                    merged[u][v].get("weight", 0) + data.get("weight", 1)
                )
                # merge speakers
                existing_speakers = merged[u][v].get("speakers", [])
                for s in data.get("speakers", []):
                    if s not in existing_speakers:
                        existing_speakers.append(s)
                if existing_speakers:
                    merged[u][v]["speakers"] = existing_speakers
                # merge contexts (capped)
                existing_contexts = merged[u][v].get("contexts", [])
                new_contexts = data.get("contexts", [])
                if len(existing_contexts) < MAX_CONTEXTS_MERGED:
                    remaining = MAX_CONTEXTS_MERGED - len(existing_contexts)
                    existing_contexts.extend(new_contexts[:remaining])
                    merged[u][v]["contexts"] = existing_contexts
            else:
                merged.add_edge(u, v, **data)
    return merged

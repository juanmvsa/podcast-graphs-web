"""Graph serialization, adjacency matrices, and file I/O.

Converts networkx graphs to JSON-serializable formats and saves them
as JSON and CSV files.
"""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
import polars as pl

from podcast_graphs.types import (
    EntityResult,
    EpisodeGraphData,
    SerializedEdge,
    ShowGraphData,
)


def graph_to_adjacency_matrix(
    graph: nx.DiGraph,
) -> tuple[list[str], list[list[int]]]:
    """Convert a networkx digraph to an adjacency matrix.

    Returns the ordered node list and the matrix as nested lists.
    """
    nodes = sorted(graph.nodes())
    if not nodes:
        return [], []
    sparse_matrix = nx.adjacency_matrix(graph, nodelist=nodes)
    matrix: list[list[int]] = sparse_matrix.toarray().tolist()
    return nodes, matrix


def graph_to_polars_adjacency(graph: nx.DiGraph) -> pl.DataFrame:
    """Convert a networkx digraph adjacency matrix to a polars DataFrame."""
    nodes, matrix = graph_to_adjacency_matrix(graph)
    if not nodes:
        return pl.DataFrame()
    data: dict[str, list[object]] = {"node": nodes}
    for i, node in enumerate(nodes):
        data[node] = [row[i] for row in matrix]
    return pl.DataFrame(data)


def serialize_edges(graph: nx.DiGraph) -> list[SerializedEdge]:
    """Serialize graph edges including contexts, sentiment, and speakers."""
    edges: list[SerializedEdge] = []
    for u, v, data in graph.edges(data=True):
        # pydantic coerces context dicts into ContextEntry and applies defaults.
        edge = SerializedEdge(
            source=u,
            target=v,
            weight=data.get("weight", 1),
            relation=data.get("relation", "mentioned_in"),
            speakers=data.get("speakers", []),
            contexts=data.get("contexts", []),
        )
        edges.append(edge)
    return edges


def serialize_graph(
    graph: nx.DiGraph,
    episode: str,
    show: str,
    entity_result: EntityResult,
) -> EpisodeGraphData:
    """Serialize a graph to a storable format with adjacency matrix."""
    nodes, matrix = graph_to_adjacency_matrix(graph)
    edges = serialize_edges(graph)

    return EpisodeGraphData(
        episode=episode,
        show=show,
        persons=entity_result.persons,
        places=entity_result.places,
        nodes=nodes,
        adjacency_matrix=matrix,
        edges=edges,
    )


def save_graph_data(
    graph_data: EpisodeGraphData | ShowGraphData,
    output_path: Path,
) -> None:
    """Save graph data as JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        # to_dict serializes pydantic edge models that asdict cannot handle.
        json.dump(graph_data.to_dict(), f, ensure_ascii=False, indent=2)


def save_adjacency_csv(graph: nx.DiGraph, output_path: Path) -> None:
    """Save adjacency matrix as CSV using polars."""
    df = graph_to_polars_adjacency(graph)
    if df.is_empty():
        return
    csv_path = output_path.with_suffix(".csv")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_csv(csv_path)

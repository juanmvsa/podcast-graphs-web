"""end-to-end smoke tests for the graph pipeline.

these exercise the paths that the pydantic migration broke: SegmentEntities
attribute access in construction, sentiment stored as a dict on edge contexts,
json serialization of pydantic edge models, and the visualization sentiment
reads. the type-only tests in test_types.py do not cover any of this.
"""

from __future__ import annotations

import json

from podcast_graphs.graph.construction import build_episode_graph
from podcast_graphs.graph.serialization import serialize_graph
from podcast_graphs.graph.visualization import visualize_graph
from podcast_graphs.types import EntityResult, SegmentEntities, TranscriptSegment


def _sample_entity_result() -> EntityResult:
    """build an entity result with one segment.

    text is kept under 10 chars so analyze_sentiment short-circuits to NEUTRAL
    and never loads the distilbert model.
    """
    return EntityResult(
        persons=["John Smith"],
        places=["Paris"],
        segment_entities=[
            SegmentEntities(
                speaker="spk1",
                speaker_name="Joe",
                persons=["John Smith"],
                places=["Paris"],
                text="hi",
                segment_index=0,
                timestamp=1.0,
            ),
        ],
    )


def test_build_episode_graph_reads_segment_attributes() -> None:
    """build_episode_graph must read SegmentEntities via attributes, not dict keys."""
    graph = build_episode_graph(_sample_entity_result())
    assert graph.has_edge("John Smith", "Paris")
    contexts = graph["John Smith"]["Paris"]["contexts"]
    # sentiment is stored as a plain dict so visualization/serialization agree.
    assert isinstance(contexts[0]["sentiment"], dict)
    assert contexts[0]["sentiment"]["label"] == "NEUTRAL"


def test_serialize_graph_round_trips_to_json() -> None:
    """to_dict + json.dumps must not choke on pydantic edge/context models."""
    graph = build_episode_graph(_sample_entity_result())
    graph_data = serialize_graph(graph, "ep1", "show1", _sample_entity_result())
    parsed = json.loads(json.dumps(graph_data.to_dict()))
    assert parsed["edges"][0]["source"] == "John Smith"
    assert parsed["edges"][0]["contexts"][0]["sentiment"]["label"] == "NEUTRAL"


def test_visualize_graph_renders_without_error(tmp_path) -> None:
    """visualize_graph reads ctx['sentiment'].get(...); a pydantic object would crash."""
    graph = build_episode_graph(_sample_entity_result())
    out = tmp_path / "graph.html"
    visualize_graph(graph, out, title="Ep 1", subtitle="show1")
    assert out.exists()
    assert out.stat().st_size > 0


def test_transcript_file_segments_validate(valid_transcript_file_data: dict) -> None:
    """raw transcript dicts validate into TranscriptSegment models (pipeline path)."""
    segments = [
        TranscriptSegment(**seg) for seg in valid_transcript_file_data["segments"]
    ]
    assert segments[0].speaker == "joe_rogan"
    assert segments[0].end > segments[0].start

"""Type definitions for the podcast graphs pipeline.

Provides typed data structures for all pipeline stages: transcript segments,
entity extraction results, graph data, edge contexts, sentiment analysis,
and topic modeling.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ── Enums ─────────────────────────────────────────────────────────────────────


class EntityType(str, Enum):
    """Entity classification produced by the NER stage."""

    PERSON = "PERSON"
    PLACE = "PLACE"


class SentimentLabel(str, Enum):
    """Sentiment classification for text snippets."""

    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


class TemporalPosition(str, Enum):
    """Position within an episode timeline."""

    EARLY = "early"
    MIDDLE = "middle"
    LATE = "late"


# ── Pydantic Models ───────────────────────────────────────────────────────────


class SentimentResult(BaseModel):
    """Result of sentiment analysis on a text snippet."""

    label: Literal["POSITIVE", "NEGATIVE", "NEUTRAL"]
    score: float = Field(ge=0.0, le=1.0, description="confidence score")
    emoji: str

    model_config = ConfigDict(frozen=True)


class TranscriptSegment(BaseModel):
    """A single segment from a speaker-labeled transcript file."""

    text: str = Field(min_length=1, description="segment text content")
    speaker: str = Field(description="speaker identifier")
    speaker_name: str | None = Field(default=None, description="resolved speaker name")
    start: float = Field(ge=0.0, description="start timestamp in seconds")
    end: float = Field(gt=0.0, description="end timestamp in seconds")

    @field_validator("end")
    @classmethod
    def end_after_start(cls, v: float, info) -> float:
        """validate that end is after start."""
        if "start" in info.data and v <= info.data["start"]:
            raise ValueError("end must be greater than start")
        return v


class ContextEntry(BaseModel):
    """A single context snippet attached to a graph edge."""

    text: str
    speaker: str
    temporal: Literal["early", "middle", "late"]
    timestamp: float = Field(ge=0.0)
    sentiment: SentimentResult
    person: str | None = None


class SegmentEntities(BaseModel):
    """Entities extracted from a single transcript segment."""

    speaker: str | None = None
    speaker_name: str | None = None
    persons: list[str] = Field(default_factory=list)
    places: list[str] = Field(default_factory=list)
    text: str | None = None
    segment_index: int | None = None
    timestamp: float | None = None


class SerializedEdge(BaseModel):
    """A graph edge serialized for JSON output."""

    source: str
    target: str
    weight: int = Field(default=1, ge=1, description="co-occurrence count")
    relation: str = Field(default="mentioned_in", description="edge relation type")
    speakers: list[str] = Field(default_factory=list)
    contexts: list[ContextEntry] = Field(default_factory=list)


# ── TypedDicts (for JSON-shaped data that flows through the pipeline) ─────────


class TopicWords(TypedDict, total=False):
    """Topic assignment for a single episode."""

    topic_id: int
    topic_words: list[str]
    topic_label: str
    curated_label: str


class RepresentativeDoc(TypedDict):
    """A representative document excerpt for a topic."""

    episode: str
    excerpt: str


class TopicSummary(TypedDict, total=False):
    """Summary of a single topic cluster."""

    topic_id: int
    topic_words: list[str]
    topic_label: str
    curated_label: str
    episode_count: int
    episodes: list[str]
    representative_docs: list[RepresentativeDoc]


class TopicMetrics(TypedDict, total=False):
    """Quality metrics for topic clustering."""

    num_topics: int
    num_outlier_episodes: int
    total_episodes: int
    topic_diversity: float


class TopicResults(TypedDict, total=False):
    """Complete output of topic clustering."""

    topics: list[TopicSummary]
    episode_topics: dict[str, TopicWords]
    topic_info: list[dict[str, object]]
    metrics: TopicMetrics


class TopicCurations(TypedDict, total=False):
    """Curated topic labels, discards, and merges from topic_labels.json."""

    labels: dict[str, str]
    discarded: list[int]
    merged: dict[int, int]


class EpisodeClusterInput(TypedDict, total=False):
    """Input data for topic clustering."""

    name: str
    show: str
    text: str
    file: str


class IndexEpisode(TypedDict):
    """An episode entry in index.json."""

    title: str
    path: str
    filename: str


class IndexShow(TypedDict, total=False):
    """A show entry in index.json."""

    name: str
    displayName: str
    episodeCount: int
    episodes: list[IndexEpisode]
    summaryPath: str | None
    topicSummaries: list[IndexEpisode]


class IndexData(TypedDict, total=False):
    """The top-level index.json structure."""

    shows: list[IndexShow]
    lastUpdated: str
    totalShows: int
    totalEpisodes: int


# ── Dataclasses (for pipeline-internal state) ────────────────────────────────


@dataclass
class EntityResult:
    """Named entities extracted from a single episode."""

    persons: list[str] = field(default_factory=list)
    places: list[str] = field(default_factory=list)
    segment_entities: list[SegmentEntities] = field(default_factory=list)


@dataclass
class EpisodeGraphData:
    """Serializable graph data for a single episode."""

    episode: str
    show: str
    persons: list[str]
    places: list[str]
    nodes: list[str]
    adjacency_matrix: list[list[int]]
    edges: list[SerializedEdge]

    def to_dict(self) -> dict[str, object]:
        """Convert to a JSON-serializable dictionary."""
        data = asdict(self)
        # asdict cannot recurse into pydantic models, so dump edges explicitly.
        data["edges"] = [edge.model_dump(mode="json") for edge in self.edges]
        return data


@dataclass
class ShowGraphData:
    """Serializable graph data for a show (aggregated across episodes)."""

    show: str
    episode_count: int
    persons: list[str]
    places: list[str]
    nodes: list[str]
    adjacency_matrix: list[list[int]]
    edges: list[SerializedEdge]

    def to_dict(self) -> dict[str, object]:
        """Convert to a JSON-serializable dictionary."""
        data = asdict(self)
        # asdict cannot recurse into pydantic models, so dump edges explicitly.
        data["edges"] = [edge.model_dump(mode="json") for edge in self.edges]
        return data


@dataclass
class ResolutionMaps:
    """Entity resolution maps and blocklists for a show."""

    person_resolution: dict[str, str] = field(default_factory=dict)
    place_resolution: dict[str, str] = field(default_factory=dict)
    person_blocklist: set[str] = field(default_factory=set)
    place_blocklist: set[str] = field(default_factory=set)

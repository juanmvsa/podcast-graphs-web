# Podcast Graphs Web - Improvement Recommendations

This document contains comprehensive suggestions for improving the podcast-graphs-web codebase to make it more readable, maintainable, robust, and efficient through the use of Pydantic and Pydantic AI.

---

## Table of Contents

1. [Replace TypedDict with Pydantic Models](#1-replace-typeddict-with-pydantic-models)
2. [Integrate Pydantic AI for AI Model Outputs](#2-integrate-pydantic-ai-for-ai-model-outputs)
3. [Add Data Validation Pipeline with Error Boundaries](#3-add-data-validation-pipeline-with-error-boundaries)
4. [Improve Modularity with Dependency Injection](#4-improve-modularity-with-dependency-injection)
5. [Add Comprehensive Error Recovery](#5-add-comprehensive-error-recovery)
6. [Create Validated Configuration Management](#6-create-validated-configuration-management)
7. [Add Data Quality Metrics and Reporting](#7-add-data-quality-metrics-and-reporting)
8. [Improve Type Safety with Strict Enums](#8-improve-type-safety-with-strict-enums)
9. [Add Pipeline Observability](#9-add-pipeline-observability)
10. [Create Unit Tests with Pydantic Fixtures](#10-create-unit-tests-with-pydantic-fixtures)
11. [Priority Summary](#priority-summary)
12. [Additional Quick Wins](#additional-quick-wins)

---

## 1. Replace TypedDict with Pydantic Models

**Priority**: 🔴 HIGH

**Current Issue**: The codebase uses `TypedDict` which provides static type checking but no runtime validation. This means invalid data can slip through until it causes errors downstream.

**Benefits**:
- Runtime validation at data ingestion points
- Automatic data coercion (e.g., string→float conversions)
- Better error messages when validation fails
- Field validation rules (min/max values, regex patterns)
- Immutability options with `frozen=True`

### Example Migration

#### Current (types.py)
```python
class TranscriptSegment(TypedDict, total=False):
    text: str
    speaker: str
    speaker_name: str
    start: float
    end: float
```

#### Proposed (with Pydantic)
```python
from pydantic import BaseModel, Field, field_validator

class TranscriptSegment(BaseModel):
    text: str = Field(min_length=1, description="Segment text content")
    speaker: str = Field(pattern=r"speaker_\d+", description="Speaker ID")
    speaker_name: str | None = Field(default=None, description="Resolved speaker name")
    start: float = Field(ge=0.0, description="Start timestamp in seconds")
    end: float = Field(gt=0.0, description="End timestamp in seconds")

    @field_validator('end')
    @classmethod
    def end_after_start(cls, v: float, info) -> float:
        if 'start' in info.data and v <= info.data['start']:
            raise ValueError('end must be greater than start')
        return v

    model_config = {'frozen': True}  # immutability
```

### Priority Files to Migrate

1. `TranscriptSegment` - validates input data integrity
2. `EntityResult` - validates NER pipeline outputs
3. `SerializedEdge` / `EpisodeGraphData` - validates serialization integrity
4. `TopicResults` - validates clustering outputs

### Implementation Example: EntityResult

```python
from pydantic import BaseModel, Field
from dataclasses import dataclass

# Current
@dataclass
class EntityResult:
    persons: list[str]
    places: list[str]
    segment_entities: list[SegmentEntities]

# Proposed
class EntityResult(BaseModel):
    persons: list[str] = Field(default_factory=list, description="Unique persons in episode")
    places: list[str] = Field(default_factory=list, description="Unique places in episode")
    segment_entities: list[SegmentEntities] = Field(
        default_factory=list,
        description="Per-segment entity associations"
    )

    @field_validator('persons', 'places')
    @classmethod
    def no_empty_strings(cls, v: list[str]) -> list[str]:
        # filter out empty entity names.
        return [entity for entity in v if entity.strip()]

    model_config = {'frozen': True}
```

---

## 2. Integrate Pydantic AI for AI Model Outputs

**Priority**: 🔴 HIGH

**Current Issue**: AI model outputs (sentiment analysis, NER) lack structured validation. Errors in model outputs propagate silently.

**Benefits**:
- Catches malformed AI outputs immediately
- Documents expected output structure
- Enables retries/fallbacks on validation failures
- Type-safe downstream consumption

### Example for Sentiment Analysis

#### Current (sentiment.py)
```python
class SentimentResult(TypedDict):
    label: str
    score: float
    emoji: str
```

#### Proposed with Pydantic AI
```python
from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent, RunContext
from typing import Literal

class SentimentResult(BaseModel):
    label: Literal["POSITIVE", "NEGATIVE", "NEUTRAL"]
    score: float = Field(ge=0.0, le=1.0, description="Confidence score")
    emoji: Literal["😊", "😞", "😐"]

    @field_validator('emoji', mode='before')
    @classmethod
    def emoji_matches_label(cls, v: str, info) -> str:
        label_emoji_map = {
            "POSITIVE": "😊",
            "NEGATIVE": "😞",
            "NEUTRAL": "😐"
        }
        expected = label_emoji_map.get(info.data.get('label'))
        if expected and v != expected:
            return expected  # auto-correct emoji based on label.
        return v

# Wrap the transformer pipeline
sentiment_agent = Agent(
    'transformers:distilbert-base-uncased-finetuned-sst-2-english',
    result_type=SentimentResult,
    system_prompt="Analyze sentiment and return structured result"
)

async def analyze_sentiment(text: str) -> SentimentResult:
    """analyze sentiment with validated output."""
    result = await sentiment_agent.run(text)
    return result.data  # guaranteed to be valid SentimentResult
```

### Alternative: Validate Existing Pipeline Output

If not using Pydantic AI's agent system, wrap existing outputs:

```python
from transformers import pipeline as hf_pipeline

class DistilBertSentimentAnalyzer:
    """distilbert sentiment analyzer with validated outputs."""

    def __init__(self):
        self._pipeline = hf_pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english",
            device=-1
        )

    def analyze(self, text: str) -> SentimentResult:
        """analyze sentiment with pydantic validation."""
        if not text or len(text.strip()) < 3:
            return SentimentResult(label="NEUTRAL", score=0.5, emoji="😐")

        try:
            # truncate to bert limit.
            truncated = text[:512]
            raw_result = self._pipeline(truncated)[0]

            # map transformer output to our schema.
            label_map = {"POSITIVE": "POSITIVE", "NEGATIVE": "NEGATIVE"}
            label = label_map.get(raw_result['label'], "NEUTRAL")
            score = raw_result['score']

            # pydantic validates automatically.
            return SentimentResult(
                label=label,
                score=score,
                emoji=self._get_emoji(label)
            )
        except Exception as e:
            # fallback to neutral on errors.
            return SentimentResult(label="NEUTRAL", score=0.5, emoji="😐")

    @staticmethod
    def _get_emoji(label: str) -> str:
        """get emoji for sentiment label."""
        return {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}[label]
```

---

## 3. Add Data Validation Pipeline with Error Boundaries

**Priority**: 🔴 HIGH

**Current Issue**: Files are loaded directly without validation. Corrupted JSON or missing fields cause cryptic errors deep in the pipeline.

### Create Validated Data Loader

Create a new file: `scripts/podcast_graphs/loaders.py`

```python
"""validated data loaders for transcript files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar, Type

from pydantic import BaseModel, ValidationError
from rich.console import Console

console = Console()
T = TypeVar('T', bound=BaseModel)


class ValidationReport(BaseModel):
    """report of validation results."""
    file_path: Path
    valid: bool
    errors: list[str] = []
    warnings: list[str] = []


def load_and_validate(
    file_path: Path,
    model: Type[T],
    strict: bool = True
) -> tuple[T | None, ValidationReport]:
    """
    load json file and validate against pydantic model.

    Args:
        file_path: path to json file.
        model: pydantic model class.
        strict: if true, raise on validation errors; if false, log and skip.

    Returns:
        (validated_data, report)
    """
    report = ValidationReport(file_path=file_path, valid=False)

    # load json.
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as e:
        report.errors.append(f"invalid json: {e}")
        if strict:
            raise
        return None, report
    except FileNotFoundError as e:
        report.errors.append(f"file not found: {e}")
        if strict:
            raise
        return None, report

    # validate against model.
    try:
        validated = model.model_validate(raw_data)
        report.valid = True
        return validated, report
    except ValidationError as e:
        report.errors.extend([str(err) for err in e.errors()])
        if strict:
            raise
        console.print(f"[yellow]validation failed for {file_path}:[/yellow]")
        for error in report.errors:
            console.print(f"  • {error}")
        return None, report


class TranscriptFile(BaseModel):
    """complete transcript file structure."""
    audio_file: str
    language: str
    segments: list[TranscriptSegment]

    @field_validator('segments')
    @classmethod
    def segments_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError('transcript must have at least one segment')
        return v


def load_transcript(file_path: Path) -> TranscriptFile | None:
    """load and validate transcript file."""
    data, report = load_and_validate(
        file_path,
        TranscriptFile,
        strict=False  # skip invalid files with warning.
    )
    return data
```

### Integrate into Pipeline

Update `pipeline.py`:

```python
from .loaders import load_transcript

def collect_raw_entities(
    nlp: Language,
    episode_files: list[Path],
    # ... other args
) -> tuple[set[str], set[str]]:
    """collect raw entities with validated inputs."""
    all_persons: set[str] = set()
    all_places: set[str] = set()
    failed_files: list[Path] = []

    for file_path in episode_files:
        # validate before processing.
        transcript = load_transcript(file_path)
        if transcript is None:
            failed_files.append(file_path)
            continue

        # rest of processing with transcript.segments.
        persons, places = extract_from_validated_transcript(nlp, transcript)
        all_persons.update(persons)
        all_places.update(places)

    if failed_files:
        console.print(f"\n[yellow]⚠ skipped {len(failed_files)} invalid files[/yellow]")
        for file_path in failed_files[:5]:  # show first 5.
            console.print(f"  • {file_path.name}")
        if len(failed_files) > 5:
            console.print(f"  ... and {len(failed_files) - 5} more")

    return all_persons, all_places
```

---

## 4. Improve Modularity with Dependency Injection

**Priority**: 🟡 MEDIUM

**Current Issue**: Hard-coded model paths and singleton patterns make testing difficult.

### Create Protocol-Based Interfaces

Create a new file: `scripts/podcast_graphs/models.py`

```python
"""model interfaces and implementations with dependency injection."""

from __future__ import annotations

from typing import Protocol
from pydantic import BaseModel

from .types import SentimentResult, EntityResult


class SentimentAnalyzer(Protocol):
    """protocol for sentiment analysis."""

    def analyze(self, text: str) -> SentimentResult:
        """analyze sentiment of text."""
        ...


class NERExtractor(Protocol):
    """protocol for named entity recognition."""

    def extract(self, text: str) -> tuple[set[str], set[str]]:
        """extract (persons, places) from text."""
        ...


# concrete implementations.
class DistilBertSentiment:
    """distilbert-based sentiment analyzer."""

    def __init__(self, model_name: str = "distilbert-base-uncased-finetuned-sst-2-english"):
        from transformers import pipeline
        self._pipeline = pipeline("sentiment-analysis", model=model_name, device=-1)

    def analyze(self, text: str) -> SentimentResult:
        """analyze sentiment with validated output."""
        if not text or len(text.strip()) < 3:
            return SentimentResult(label="NEUTRAL", score=0.5, emoji="😐")

        truncated = text[:512]
        result = self._pipeline(truncated)[0]

        label_map = {"POSITIVE": "POSITIVE", "NEGATIVE": "NEGATIVE"}
        label = label_map.get(result['label'], "NEUTRAL")

        return SentimentResult(
            label=label,
            score=result['score'],
            emoji={"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}[label]
        )


class SpacyNER:
    """spacy-based ner extractor."""

    def __init__(self, model_name: str = "en_core_web_lg"):
        import spacy
        self.nlp = spacy.load(model_name)

    def extract(self, text: str) -> tuple[set[str], set[str]]:
        """extract entities from text."""
        doc = self.nlp(text)
        persons = {ent.text for ent in doc.ents if ent.label_ == "PERSON"}
        places = {ent.text for ent in doc.ents if ent.label_ in {"GPE", "LOC", "FAC"}}
        return persons, places


# configuration container.
class PipelineConfig(BaseModel):
    """configuration for entire pipeline."""
    sentiment_model: str = "distilbert-base-uncased-finetuned-sst-2-english"
    ner_model: str = "en_core_web_lg"
    batch_size: int = 256
    max_contexts_per_edge: int = 3
    max_contexts_merged: int = 5
    max_contexts_display: int = 2
    early_threshold: float = 0.33
    late_threshold: float = 0.66

    model_config = {'frozen': True}


# factory function.
def create_pipeline_dependencies(config: PipelineConfig | None = None):
    """create pipeline with injected dependencies."""
    if config is None:
        config = PipelineConfig()

    return {
        'sentiment_analyzer': DistilBertSentiment(config.sentiment_model),
        'ner_extractor': SpacyNER(config.ner_model),
        'config': config
    }
```

### Usage in Pipeline

```python
from .models import create_pipeline_dependencies, PipelineConfig

def process_show(
    show_dir: Path,
    config: PipelineConfig | None = None
):
    """process show with dependency injection."""
    # create dependencies.
    deps = create_pipeline_dependencies(config)

    sentiment_analyzer = deps['sentiment_analyzer']
    ner_extractor = deps['ner_extractor']
    pipeline_config = deps['config']

    # use injected dependencies.
    for episode in show_dir.glob("*.json"):
        # ... use sentiment_analyzer.analyze(text)
        # ... use ner_extractor.extract(text)
        pass
```

### Benefits

- Easy to swap models without code changes
- Testable with mock implementations
- Configuration as data (can load from YAML/JSON)
- Clear dependency graph

---

## 5. Add Comprehensive Error Recovery

**Priority**: 🟡 MEDIUM

**Current Issue**: A single failed episode stops the entire show processing.

### Create Error Boundary Wrapper

Add to `scripts/podcast_graphs/utils/error_handling.py`:

```python
"""error handling utilities for graceful degradation."""

from __future__ import annotations

from typing import TypeVar, Callable, Generic
from functools import wraps
from pathlib import Path

from pydantic import BaseModel
from rich.console import Console

console = Console()
T = TypeVar('T')


class ProcessingResult(BaseModel, Generic[T]):
    """result of processing operation."""
    success: bool
    data: T | None = None
    error: str | None = None
    file_path: Path | None = None

    class Config:
        arbitrary_types_allowed = True  # allow Path type.


def with_error_boundary(
    operation_name: str,
    fallback: T | None = None
) -> Callable:
    """
    decorator to add error boundary around operations.

    Args:
        operation_name: human-readable operation description.
        fallback: fallback value on error.

    Returns:
        decorated function that returns ProcessingResult.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., ProcessingResult[T]]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> ProcessingResult[T]:
            try:
                result = func(*args, **kwargs)
                return ProcessingResult(success=True, data=result)
            except Exception as e:
                console.print(f"[red]✗ {operation_name} failed: {e}[/red]")
                return ProcessingResult(
                    success=False,
                    error=str(e),
                    data=fallback
                )
        return wrapper
    return decorator


def with_file_error_boundary(operation_name: str):
    """
    decorator for file processing operations.

    Automatically extracts file_path from first argument.
    """
    def decorator(func: Callable[[Path, ...], T]) -> Callable[[Path, ...], ProcessingResult[T]]:
        @wraps(func)
        def wrapper(file_path: Path, *args, **kwargs) -> ProcessingResult[T]:
            try:
                result = func(file_path, *args, **kwargs)
                return ProcessingResult(
                    success=True,
                    data=result,
                    file_path=file_path
                )
            except Exception as e:
                console.print(f"[red]✗ {operation_name} failed for {file_path.name}: {e}[/red]")
                return ProcessingResult(
                    success=False,
                    error=str(e),
                    file_path=file_path,
                    data=None
                )
        return wrapper
    return decorator
```

### Usage in Pipeline

```python
from .utils.error_handling import with_file_error_boundary, ProcessingResult
from .types import EntityResult, EpisodeGraphData

@with_file_error_boundary("entity extraction")
def extract_episode_entities(
    file_path: Path,
    nlp,
    # ... other args
) -> EntityResult:
    """extract entities from episode file."""
    # existing implementation.
    # if this raises, error boundary catches it.
    ...

@with_file_error_boundary("graph construction")
def build_episode_graph(
    file_path: Path,
    entity_result: EntityResult
) -> EpisodeGraphData:
    """build graph from entity result."""
    # existing implementation.
    ...

# in pipeline orchestration.
def process_show(episodes: list[Path]) -> ShowGraphData:
    """process show with partial failure handling."""
    episode_results: list[ProcessingResult[EpisodeGraphData]] = []

    for ep in episodes:
        # extract entities (returns ProcessingResult).
        entity_result_wrapper = extract_episode_entities(ep, nlp)
        if not entity_result_wrapper.success:
            episode_results.append(entity_result_wrapper)
            continue

        # build graph (returns ProcessingResult).
        graph_result = build_episode_graph(ep, entity_result_wrapper.data)
        episode_results.append(graph_result)

    # filter successful results.
    successful = [r.data for r in episode_results if r.success and r.data]
    failed = [r for r in episode_results if not r.success]

    # report failures.
    if failed:
        console.print(f"\n[yellow]⚠ {len(failed)}/{len(episodes)} episodes failed[/yellow]")
        for r in failed[:10]:  # show first 10.
            console.print(f"  • {r.file_path.name if r.file_path else 'unknown'}: {r.error}")
        if len(failed) > 10:
            console.print(f"  ... and {len(failed) - 10} more")

    # continue with successful episodes.
    if not successful:
        raise ValueError(f"all {len(episodes)} episodes failed processing")

    console.print(f"[green]✓ successfully processed {len(successful)} episodes[/green]")
    return merge_episodes(successful)
```

---

## 6. Create Validated Configuration Management

**Priority**: 🟡 MEDIUM

**Current Issue**: Constants scattered in `constants.py`, hard to override per-show or via environment.

### Use Pydantic Settings

Create `scripts/podcast_graphs/config.py`:

```python
"""hierarchical configuration management with pydantic settings."""

from __future__ import annotations

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EntityProcessingConfig(BaseSettings):
    """entity extraction and filtering configuration."""
    min_entity_length: int = Field(
        default=3,
        description="minimum character length for entities"
    )
    min_single_token_length: int = Field(
        default=5,
        description="minimum length for single-token entities"
    )
    max_entity_tokens: int = Field(
        default=4,
        description="maximum number of tokens per entity"
    )

    # can override via environment variables.
    model_config = SettingsConfigDict(env_prefix='ENTITY_')


class GraphConfig(BaseSettings):
    """graph construction configuration."""
    max_contexts_per_edge: int = Field(
        default=3,
        description="max contexts per edge during extraction"
    )
    max_contexts_merged: int = Field(
        default=5,
        description="max contexts per edge after merging"
    )
    max_contexts_display: int = Field(
        default=2,
        description="contexts shown in visualization tooltip"
    )
    max_segment_text: int = Field(
        default=200,
        description="max characters per segment context"
    )

    early_threshold: float = Field(
        default=0.33,
        ge=0.0,
        le=1.0,
        description="threshold for 'early' temporal label"
    )
    late_threshold: float = Field(
        default=0.66,
        ge=0.0,
        le=1.0,
        description="threshold for 'late' temporal label"
    )

    model_config = SettingsConfigDict(env_prefix='GRAPH_')


class PipelineSettings(BaseSettings):
    """top-level pipeline settings."""
    transcripts_dir: Path = Field(
        default=Path("transcripts_with_speaker_labels_postprocessed_with_utterance_and_document_labels"),
        description="directory containing transcript files"
    )
    output_dir: Path = Field(
        default=Path("graphs"),
        description="output directory for generated graphs"
    )

    nlp_model: str = Field(
        default="en_core_web_lg",
        description="spacy model for ner"
    )
    nlp_batch_size: int = Field(
        default=256,
        description="batch size for spacy nlp.pipe()"
    )

    sentiment_model: str = Field(
        default="distilbert-base-uncased-finetuned-sst-2-english",
        description="huggingface model for sentiment analysis"
    )

    # nested configs.
    entity: EntityProcessingConfig = Field(
        default_factory=EntityProcessingConfig,
        description="entity processing configuration"
    )
    graph: GraphConfig = Field(
        default_factory=GraphConfig,
        description="graph construction configuration"
    )

    # can load from .env, environment, or yaml.
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
        frozen=True  # immutable after creation.
    )


# singleton instance.
_settings: PipelineSettings | None = None

def get_settings() -> PipelineSettings:
    """get or create settings singleton."""
    global _settings
    if _settings is None:
        _settings = PipelineSettings()
    return _settings
```

### Usage

```python
from .config import get_settings

def process_pipeline():
    """process pipeline using settings."""
    settings = get_settings()

    # access nested config.
    max_contexts = settings.graph.max_contexts_per_edge
    min_length = settings.entity.min_entity_length

    # use paths.
    transcript_files = settings.transcripts_dir.glob("*.json")
```

### Override via Environment

```bash
# override max contexts per edge.
export GRAPH__MAX_CONTEXTS_PER_EDGE=5

# override entity min length.
export ENTITY__MIN_ENTITY_LENGTH=4

# run pipeline with overrides.
uv run scripts/generate_entity_graphs.py
```

### Override via .env File

Create `.env` in project root:

```bash
# graph settings.
GRAPH__MAX_CONTEXTS_PER_EDGE=5
GRAPH__MAX_CONTEXTS_DISPLAY=3

# entity settings.
ENTITY__MIN_ENTITY_LENGTH=4
ENTITY__MAX_ENTITY_TOKENS=5

# paths.
TRANSCRIPTS_DIR=/path/to/transcripts
OUTPUT_DIR=/path/to/output
```

---

## 7. Add Data Quality Metrics and Reporting

**Priority**: 🟡 MEDIUM

**Current Issue**: No visibility into data quality issues (low-confidence entities, missing speakers, etc.)

### Create Quality Metrics Module

Create `scripts/podcast_graphs/quality.py`:

```python
"""data quality metrics and reporting."""

from __future__ import annotations

from collections import Counter
from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table

console = Console()


class QualityMetrics(BaseModel):
    """quality metrics for processed data."""
    total_segments: int = 0
    segments_with_entities: int = 0
    segments_without_speaker: int = 0

    total_entities_extracted: int = 0
    entities_filtered_as_garbage: int = 0
    entities_resolved_via_wikipedia: int = 0
    entities_merged_via_abbreviation: int = 0
    entities_merged_via_partial_name: int = 0

    low_confidence_sentiments: int = 0
    failed_sentiment_analyses: int = 0

    entity_frequency: dict[str, int] = Field(default_factory=dict)
    speaker_distribution: dict[str, int] = Field(default_factory=dict)

    def coverage_rate(self) -> float:
        """fraction of segments with entities."""
        if self.total_segments == 0:
            return 0.0
        return self.segments_with_entities / self.total_segments

    def garbage_rate(self) -> float:
        """fraction of extracted entities filtered as garbage."""
        if self.total_entities_extracted == 0:
            return 0.0
        return self.entities_filtered_as_garbage / self.total_entities_extracted

    def merge_rate(self) -> float:
        """fraction of entities that were merged."""
        merged = (
            self.entities_merged_via_abbreviation +
            self.entities_merged_via_partial_name +
            self.entities_resolved_via_wikipedia
        )
        if self.total_entities_extracted == 0:
            return 0.0
        return merged / self.total_entities_extracted

    def print_report(self):
        """print formatted quality report."""
        console.print("\n[bold cyan]📊 data quality metrics[/bold cyan]")

        # overview table.
        table = Table(title="overview")
        table.add_column("metric", style="cyan")
        table.add_column("value", style="green")

        table.add_row("segments processed", str(self.total_segments))
        table.add_row("entity coverage", f"{self.coverage_rate():.1%}")
        table.add_row("garbage filter rate", f"{self.garbage_rate():.1%}")
        table.add_row("entity merge rate", f"{self.merge_rate():.1%}")
        table.add_row("wikipedia resolutions", str(self.entities_resolved_via_wikipedia))

        console.print(table)

        # warnings.
        if self.segments_without_speaker > 0:
            console.print(
                f"[yellow]⚠ {self.segments_without_speaker} segments without speaker[/yellow]"
            )

        if self.low_confidence_sentiments > 0:
            console.print(
                f"[yellow]⚠ {self.low_confidence_sentiments} low confidence sentiments[/yellow]"
            )

        if self.failed_sentiment_analyses > 0:
            console.print(
                f"[red]✗ {self.failed_sentiment_analyses} failed sentiment analyses[/red]"
            )

        # top entities.
        if self.entity_frequency:
            console.print(f"\n[bold]top 10 entities:[/bold]")
            counter = Counter(self.entity_frequency)
            for entity, count in counter.most_common(10):
                console.print(f"  • {entity}: {count}")

        # speaker distribution.
        if self.speaker_distribution:
            console.print(f"\n[bold]speaker distribution:[/bold]")
            counter = Counter(self.speaker_distribution)
            for speaker, count in counter.most_common(5):
                console.print(f"  • {speaker}: {count}")


class MetricsTracker:
    """helper class to track metrics during processing."""

    def __init__(self):
        self.metrics = QualityMetrics()

    def track_segment(self, has_entities: bool, has_speaker: bool):
        """track segment processing."""
        self.metrics.total_segments += 1
        if has_entities:
            self.metrics.segments_with_entities += 1
        if not has_speaker:
            self.metrics.segments_without_speaker += 1

    def track_entity_extraction(self, extracted: int, filtered: int):
        """track entity extraction."""
        self.metrics.total_entities_extracted += extracted
        self.metrics.entities_filtered_as_garbage += filtered

    def track_entity_resolution(
        self,
        wikipedia: int = 0,
        abbreviation: int = 0,
        partial_name: int = 0
    ):
        """track entity resolution."""
        self.metrics.entities_resolved_via_wikipedia += wikipedia
        self.metrics.entities_merged_via_abbreviation += abbreviation
        self.metrics.entities_merged_via_partial_name += partial_name

    def track_sentiment(self, success: bool, confidence: float):
        """track sentiment analysis."""
        if not success:
            self.metrics.failed_sentiment_analyses += 1
        elif confidence < 0.6:
            self.metrics.low_confidence_sentiments += 1

    def track_entity(self, entity: str):
        """track entity frequency."""
        self.metrics.entity_frequency[entity] = (
            self.metrics.entity_frequency.get(entity, 0) + 1
        )

    def track_speaker(self, speaker: str):
        """track speaker distribution."""
        self.metrics.speaker_distribution[speaker] = (
            self.metrics.speaker_distribution.get(speaker, 0) + 1
        )

    def get_metrics(self) -> QualityMetrics:
        """get accumulated metrics."""
        return self.metrics
```

### Integrate into Pipeline

```python
from .quality import MetricsTracker

def extract_episode_entities(
    nlp,
    segments,
    # ... other args
) -> tuple[EntityResult, QualityMetrics]:
    """extract entities with quality tracking."""
    tracker = MetricsTracker()

    for segment in segments:
        has_speaker = bool(segment.get('speaker'))

        # extract entities.
        persons, places = extract_from_segment(nlp, segment)
        has_entities = bool(persons or places)

        tracker.track_segment(has_entities, has_speaker)

        # track extracted vs filtered.
        raw_entities = len(persons) + len(places)
        filtered = filter_garbage_entities(persons, places)
        tracker.track_entity_extraction(raw_entities, len(filtered))

        # track entity frequencies.
        for person in persons:
            tracker.track_entity(person)
        for place in places:
            tracker.track_entity(place)

        # track speaker.
        if has_speaker:
            tracker.track_speaker(segment['speaker'])

    return entity_result, tracker.get_metrics()


# in pipeline orchestration.
def process_show(episodes: list[Path]):
    """process show with quality reporting."""
    all_metrics: list[QualityMetrics] = []

    for episode in episodes:
        entity_result, metrics = extract_episode_entities(...)
        all_metrics.append(metrics)

    # aggregate metrics.
    combined = aggregate_metrics(all_metrics)
    combined.print_report()
```

---

## 8. Improve Type Safety with Strict Enums

**Priority**: 🟢 LOW

**Current Issue**: String literals for sentiments, entity types can have typos.

**Enhancement**: Already using `Enum`, but enforce stricter usage with Literal types in Pydantic models.

### Implementation

```python
# in types.py
from enum import Enum
from typing import Literal

# keep enums for logic.
class SentimentLabel(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"

class EntityType(str, Enum):
    PERSON = "PERSON"
    PLACE = "PLACE"

class TemporalPosition(str, Enum):
    EARLY = "early"
    MIDDLE = "middle"
    LATE = "late"

# create literal types for pydantic.
SentimentLiteral = Literal["POSITIVE", "NEGATIVE", "NEUTRAL"]
EntityTypeLiteral = Literal["PERSON", "PLACE"]
TemporalPositionLiteral = Literal["early", "middle", "late"]

# use in pydantic models.
class SentimentResult(BaseModel):
    label: SentimentLiteral  # enforces exact string values.
    score: float = Field(ge=0.0, le=1.0)
    emoji: str

class ContextEntry(BaseModel):
    text: str
    speaker: str
    temporal: TemporalPositionLiteral
    timestamp: float
    sentiment: SentimentResult
```

### Additional String Enums

```python
class RelationType(str, Enum):
    """edge relation types."""
    MENTIONED_IN = "mentioned_in"
    CO_OCCURRED = "co_occurred"

class GraphOutputFormat(str, Enum):
    """supported output formats."""
    JSON = "json"
    CSV = "csv"
    HTML = "html"

class LogLevel(str, Enum):
    """logging levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
```

---

## 9. Add Pipeline Observability

**Priority**: 🟢 LOW

**Current Issue**: Hard to debug performance bottlenecks or track progress.

### Create Observability Module

Create `scripts/podcast_graphs/observability.py`:

```python
"""pipeline observability and performance tracking."""

from __future__ import annotations

import time
from contextlib import contextmanager
from pydantic import BaseModel, Field
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, BarColumn

console = Console()


class OperationTiming(BaseModel):
    """timing for a pipeline operation."""
    operation: str
    duration_seconds: float
    items_processed: int = 0

    def throughput(self) -> float:
        """items per second."""
        if self.duration_seconds == 0:
            return 0.0
        return self.items_processed / self.duration_seconds

    def format_duration(self) -> str:
        """format duration as human-readable string."""
        if self.duration_seconds < 1:
            return f"{self.duration_seconds * 1000:.0f}ms"
        elif self.duration_seconds < 60:
            return f"{self.duration_seconds:.1f}s"
        else:
            minutes = int(self.duration_seconds // 60)
            seconds = self.duration_seconds % 60
            return f"{minutes}m {seconds:.1f}s"


class PerformanceReport(BaseModel):
    """performance report for pipeline run."""
    total_duration_seconds: float
    timings: list[OperationTiming] = Field(default_factory=list)

    def add_timing(self, timing: OperationTiming):
        """add operation timing."""
        self.timings.append(timing)

    def print_report(self):
        """print formatted performance report."""
        console.print("\n[bold cyan]⚡ performance report[/bold cyan]")
        console.print(f"total duration: {self._format_duration(self.total_duration_seconds)}")

        for timing in self.timings:
            msg = f"  • {timing.operation}: {timing.format_duration()}"
            if timing.items_processed > 0:
                msg += f" ({timing.throughput():.1f} items/sec)"
            console.print(msg)

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """format duration."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"


@contextmanager
def timed_operation(operation: str, items: int = 0):
    """
    context manager for timing operations.

    Example:
        with timed_operation("entity extraction", len(episodes)):
            # ... process episodes
    """
    console.print(f"[cyan]▶ starting {operation}...[/cyan]")
    start = time.perf_counter()

    try:
        yield
    finally:
        duration = time.perf_counter() - start
        timing = OperationTiming(
            operation=operation,
            duration_seconds=duration,
            items_processed=items
        )

        msg = f"[green]✓ {operation} completed in {timing.format_duration()}[/green]"
        if items > 0:
            msg += f" ([bold]{timing.throughput():.1f}[/bold] items/sec)"
        console.print(msg)


@contextmanager
def progress_bar(description: str, total: int):
    """
    context manager for progress bar.

    Example:
        with progress_bar("processing episodes", len(episodes)) as progress:
            for episode in progress.track(episodes):
                # ... process episode
    """
    with Progress(
        SpinnerColumn(),
        *Progress.get_default_columns(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task(description, total=total)

        class ProgressTracker:
            def track(self, items):
                for item in items:
                    yield item
                    progress.advance(task)

        yield ProgressTracker()
```

### Usage in Pipeline

```python
from .observability import timed_operation, progress_bar, PerformanceReport

def process_show(episodes: list[Path]) -> ShowGraphData:
    """process show with observability."""
    report = PerformanceReport(total_duration_seconds=0)
    start = time.perf_counter()

    # entity extraction with timing.
    with timed_operation("entity extraction", len(episodes)):
        with progress_bar("extracting entities", len(episodes)) as progress:
            for episode in progress.track(episodes):
                extract_entities(episode)

    # graph construction with timing.
    with timed_operation("graph construction", len(episodes)):
        graphs = [build_graph(ep) for ep in episodes]

    # sentiment analysis with timing.
    with timed_operation("sentiment analysis"):
        analyze_sentiments(graphs)

    total_duration = time.perf_counter() - start
    report.total_duration_seconds = total_duration
    report.print_report()

    return merged_graph
```

---

## 10. Create Unit Tests with Pydantic Fixtures

**Priority**: 🔴 HIGH

**Current Issue**: No visible test suite for data validation.

### Create Test Suite

Create `tests/test_validation.py`:

```python
"""unit tests for pydantic validation."""

import pytest
from pydantic import ValidationError
from scripts.podcast_graphs.types import (
    TranscriptSegment,
    SentimentResult,
    EntityResult,
)


class TestTranscriptSegment:
    """tests for transcript segment validation."""

    def test_valid_segment(self):
        """test valid segment creation."""
        segment = TranscriptSegment(
            text="hello world",
            speaker="speaker_01",
            start=0.0,
            end=5.0
        )
        assert segment.text == "hello world"
        assert segment.speaker == "speaker_01"
        assert segment.start == 0.0
        assert segment.end == 5.0

    def test_end_before_start_raises_error(self):
        """test that end before start raises validation error."""
        with pytest.raises(ValidationError) as exc:
            TranscriptSegment(
                text="hello",
                speaker="speaker_01",
                start=10.0,
                end=5.0
            )
        assert "end must be greater than start" in str(exc.value)

    def test_negative_timestamp_raises_error(self):
        """test that negative timestamp raises error."""
        with pytest.raises(ValidationError):
            TranscriptSegment(
                text="hello",
                speaker="speaker_01",
                start=-1.0,
                end=5.0
            )

    def test_empty_text_raises_error(self):
        """test that empty text raises error."""
        with pytest.raises(ValidationError):
            TranscriptSegment(
                text="",
                speaker="speaker_01",
                start=0.0,
                end=5.0
            )

    def test_invalid_speaker_pattern_raises_error(self):
        """test that invalid speaker pattern raises error."""
        with pytest.raises(ValidationError):
            TranscriptSegment(
                text="hello",
                speaker="john_doe",  # should be speaker_XX.
                start=0.0,
                end=5.0
            )

    def test_speaker_name_optional(self):
        """test that speaker_name is optional."""
        segment = TranscriptSegment(
            text="hello",
            speaker="speaker_01",
            start=0.0,
            end=5.0
        )
        assert segment.speaker_name is None

        segment_with_name = TranscriptSegment(
            text="hello",
            speaker="speaker_01",
            speaker_name="john doe",
            start=0.0,
            end=5.0
        )
        assert segment_with_name.speaker_name == "john doe"


class TestSentimentResult:
    """tests for sentiment result validation."""

    def test_valid_positive_sentiment(self):
        """test valid positive sentiment."""
        result = SentimentResult(
            label="POSITIVE",
            score=0.95,
            emoji="😊"
        )
        assert result.label == "POSITIVE"
        assert result.score == 0.95
        assert result.emoji == "😊"

    def test_valid_negative_sentiment(self):
        """test valid negative sentiment."""
        result = SentimentResult(
            label="NEGATIVE",
            score=0.85,
            emoji="😞"
        )
        assert result.label == "NEGATIVE"

    def test_valid_neutral_sentiment(self):
        """test valid neutral sentiment."""
        result = SentimentResult(
            label="NEUTRAL",
            score=0.50,
            emoji="😐"
        )
        assert result.label == "NEUTRAL"

    def test_score_below_zero_raises_error(self):
        """test that score below 0 raises error."""
        with pytest.raises(ValidationError):
            SentimentResult(
                label="POSITIVE",
                score=-0.1,
                emoji="😊"
            )

    def test_score_above_one_raises_error(self):
        """test that score above 1 raises error."""
        with pytest.raises(ValidationError):
            SentimentResult(
                label="POSITIVE",
                score=1.5,
                emoji="😊"
            )

    def test_invalid_label_raises_error(self):
        """test that invalid label raises error."""
        with pytest.raises(ValidationError):
            SentimentResult(
                label="HAPPY",  # not in literal type.
                score=0.9,
                emoji="😊"
            )


class TestEntityResult:
    """tests for entity result validation."""

    def test_valid_entity_result(self):
        """test valid entity result."""
        result = EntityResult(
            persons=["joe rogan", "elon musk"],
            places=["texas", "california"],
            segment_entities=[]
        )
        assert len(result.persons) == 2
        assert len(result.places) == 2

    def test_empty_entity_result(self):
        """test empty entity result."""
        result = EntityResult(
            persons=[],
            places=[],
            segment_entities=[]
        )
        assert result.persons == []
        assert result.places == []

    def test_filters_empty_entity_names(self):
        """test that empty entity names are filtered."""
        result = EntityResult(
            persons=["joe rogan", "", "  ", "elon musk"],
            places=["texas", ""],
            segment_entities=[]
        )
        # validator should filter empty strings.
        assert "" not in result.persons
        assert "  " not in result.persons


@pytest.fixture
def sample_transcript_segment():
    """fixture for sample transcript segment."""
    return TranscriptSegment(
        text="this is a test segment",
        speaker="speaker_01",
        speaker_name="test speaker",
        start=0.0,
        end=10.0
    )


@pytest.fixture
def sample_sentiment_result():
    """fixture for sample sentiment result."""
    return SentimentResult(
        label="POSITIVE",
        score=0.95,
        emoji="😊"
    )


def test_segment_immutability(sample_transcript_segment):
    """test that segments are immutable."""
    with pytest.raises(ValidationError):
        sample_transcript_segment.text = "modified"  # should fail if frozen.
```

### Create Test for Data Loaders

Create `tests/test_loaders.py`:

```python
"""tests for data loaders."""

import pytest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.podcast_graphs.loaders import (
    load_and_validate,
    load_transcript,
    TranscriptFile,
    ValidationReport
)
from scripts.podcast_graphs.types import TranscriptSegment


@pytest.fixture
def valid_transcript_data():
    """fixture for valid transcript data."""
    return {
        "audio_file": "test.mp3",
        "language": "en",
        "segments": [
            {
                "text": "hello world",
                "speaker": "speaker_01",
                "start": 0.0,
                "end": 5.0
            }
        ]
    }


@pytest.fixture
def invalid_transcript_data():
    """fixture for invalid transcript data."""
    return {
        "audio_file": "test.mp3",
        "language": "en",
        "segments": [
            {
                "text": "hello",
                "speaker": "invalid_speaker",  # wrong pattern.
                "start": 10.0,
                "end": 5.0  # end before start.
            }
        ]
    }


def test_load_valid_transcript(valid_transcript_data):
    """test loading valid transcript."""
    with TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.json"
        with open(file_path, 'w') as f:
            json.dump(valid_transcript_data, f)

        data, report = load_and_validate(file_path, TranscriptFile, strict=True)

        assert data is not None
        assert report.valid is True
        assert len(report.errors) == 0
        assert data.audio_file == "test.mp3"
        assert len(data.segments) == 1


def test_load_invalid_transcript_strict(invalid_transcript_data):
    """test loading invalid transcript in strict mode."""
    with TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.json"
        with open(file_path, 'w') as f:
            json.dump(invalid_transcript_data, f)

        with pytest.raises(ValidationError):
            load_and_validate(file_path, TranscriptFile, strict=True)


def test_load_invalid_transcript_non_strict(invalid_transcript_data):
    """test loading invalid transcript in non-strict mode."""
    with TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.json"
        with open(file_path, 'w') as f:
            json.dump(invalid_transcript_data, f)

        data, report = load_and_validate(file_path, TranscriptFile, strict=False)

        assert data is None
        assert report.valid is False
        assert len(report.errors) > 0


def test_load_malformed_json():
    """test loading malformed json file."""
    with TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.json"
        with open(file_path, 'w') as f:
            f.write("{invalid json")

        data, report = load_and_validate(file_path, TranscriptFile, strict=False)

        assert data is None
        assert report.valid is False
        assert any("invalid json" in err.lower() for err in report.errors)


def test_load_nonexistent_file():
    """test loading nonexistent file."""
    file_path = Path("/nonexistent/path.json")

    data, report = load_and_validate(file_path, TranscriptFile, strict=False)

    assert data is None
    assert report.valid is False
    assert any("not found" in err.lower() for err in report.errors)
```

### Run Tests

```bash
# install pytest.
uv add --dev pytest

# run all tests.
uv run pytest tests/

# run with coverage.
uv add --dev pytest-cov
uv run pytest tests/ --cov=scripts/podcast_graphs --cov-report=html

# run specific test file.
uv run pytest tests/test_validation.py -v
```

---

## Priority Summary

### 🔴 **HIGH PRIORITY** (Do These First)

**Estimated Total Time: 8-12 hours**

1. **Migrate TypedDict → Pydantic Models** (`types.py`)
   - Immediate runtime validation
   - Catches data errors at boundaries
   - **Estimated: 2-3 hours**

2. **Add Validated Data Loaders** (`loaders.py`)
   - Prevents corrupted data from entering pipeline
   - Graceful error handling
   - **Estimated: 1-2 hours**

3. **Integrate Pydantic AI for Model Outputs**
   - Validates AI model responses
   - Enables structured retry logic
   - **Estimated: 2-4 hours**

4. **Create Unit Tests with Pydantic**
   - Validates that validation works
   - Documents expected data shapes
   - **Estimated: 2-3 hours**

### 🟡 **MEDIUM PRIORITY** (Next Steps)

**Estimated Total Time: 10-15 hours**

5. **Dependency Injection for Models** (`models.py`)
   - Makes code testable and configurable
   - **Estimated: 2-3 hours**

6. **Error Boundaries with Recovery** (`ProcessingResult` wrapper)
   - Graceful degradation on failures
   - **Estimated: 2-3 hours**

7. **Pydantic Settings for Configuration** (`config.py`)
   - Centralized, validated configuration
   - **Estimated: 2-3 hours**

8. **Quality Metrics Tracking** (`quality.py`)
   - Visibility into data quality
   - **Estimated: 3-4 hours**

### 🟢 **LOW PRIORITY** (Nice to Have)

**Estimated Total Time: 4-6 hours**

9. **Stricter Literal Types**
   - Enhanced type safety
   - **Estimated: 1-2 hours**

10. **Pipeline Observability** (`observability.py`)
    - Performance tracking and debugging
    - **Estimated: 2-3 hours**

---

## Additional Quick Wins

### 1. Add Docstring Examples with Expected Types

```python
def extract_entities(text: str) -> EntityResult:
    """
    extract entities from text.

    Args:
        text: input text to analyze.

    Returns:
        entityresult with persons and places.

    Example:
        >>> extract_entities("joe visited paris")
        EntityResult(persons=['joe'], places=['paris'], segment_entities=[])
    """
    ...
```

### 2. Use `frozenset` Return Types

```python
def get_person_stopwords() -> frozenset[str]:
    """get immutable set of person stopwords."""
    return PERSON_STOPWORDS  # already immutable.

def get_place_stopwords() -> frozenset[str]:
    """get immutable set of place stopwords."""
    return PLACE_STOPWORDS
```

### 3. Add Type Narrowing Guards

```python
from typing import TypeGuard

def is_person_entity(entity: str, entity_type: EntityType) -> TypeGuard[str]:
    """type guard for person entities."""
    return entity_type == EntityType.PERSON

def is_place_entity(entity: str, entity_type: EntityType) -> TypeGuard[str]:
    """type guard for place entities."""
    return entity_type == EntityType.PLACE

# usage.
if is_person_entity(entity, entity_type):
    # type checker knows entity is a person here.
    process_person(entity)
```

### 4. Replace Magic Strings with String Enums

```python
class RelationType(str, Enum):
    """edge relation types."""
    MENTIONED_IN = "mentioned_in"
    CO_OCCURRED = "co_occurred"

class GraphOutputFormat(str, Enum):
    """supported output formats."""
    JSON = "json"
    CSV = "csv"
    HTML = "html"

class LogLevel(str, Enum):
    """logging levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
```

### 5. Add Result Types for Operations

```python
from typing import Generic, TypeVar

T = TypeVar('T')
E = TypeVar('E')

class Result(BaseModel, Generic[T, E]):
    """result type for operations that can fail."""
    success: bool
    value: T | None = None
    error: E | None = None

    @classmethod
    def ok(cls, value: T) -> Result[T, E]:
        """create successful result."""
        return cls(success=True, value=value)

    @classmethod
    def err(cls, error: E) -> Result[T, E]:
        """create error result."""
        return cls(success=False, error=error)

    def unwrap(self) -> T:
        """get value or raise."""
        if not self.success or self.value is None:
            raise ValueError(f"called unwrap on error: {self.error}")
        return self.value

    def unwrap_or(self, default: T) -> T:
        """get value or default."""
        if not self.success or self.value is None:
            return default
        return self.value

# usage.
def process_file(path: Path) -> Result[EntityResult, str]:
    """process file returning result."""
    try:
        data = load_file(path)
        entities = extract_entities(data)
        return Result.ok(entities)
    except Exception as e:
        return Result.err(str(e))

# calling code.
result = process_file(path)
if result.success:
    entities = result.unwrap()
    # ... use entities
else:
    console.print(f"error: {result.error}")
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [ ] Migrate core types to Pydantic (`TranscriptSegment`, `SentimentResult`, `EntityResult`)
- [ ] Create validated data loaders (`loaders.py`)
- [ ] Add basic unit tests for validation

### Phase 2: AI Integration (Week 2)
- [ ] Integrate Pydantic AI for sentiment analysis
- [ ] Add error boundaries around AI operations
- [ ] Create quality metrics tracking

### Phase 3: Configuration & DI (Week 3)
- [ ] Implement Pydantic Settings configuration
- [ ] Add dependency injection for models
- [ ] Migrate constants to configuration

### Phase 4: Observability (Week 4)
- [ ] Add pipeline observability
- [ ] Create performance reporting
- [ ] Add comprehensive error recovery

### Phase 5: Polish (Week 5)
- [ ] Complete test coverage
- [ ] Add documentation and examples
- [ ] Performance optimization based on metrics

---

## Next Steps

To get started, I recommend:

1. **Start with `TranscriptSegment` migration** - This is the entry point for all data
2. **Add `loaders.py` module** - Validate data at the boundary
3. **Write tests first** - Use TDD to ensure validation works correctly
4. **Gradually migrate remaining types** - One module at a time

Would you like me to implement any of these improvements? I can start with the highest priority items and create working code.

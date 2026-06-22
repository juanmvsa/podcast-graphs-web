"""tests for pydantic type validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from podcast_graphs.types import SentimentResult, TranscriptSegment, ContextEntry, SerializedEdge


class TestSentimentResult:
    """tests for SentimentResult validation."""

    def test_valid_positive_sentiment(self, valid_sentiment_data: dict) -> None:
        """test valid positive sentiment creates successfully."""
        result = SentimentResult(**valid_sentiment_data)
        assert result.label == "POSITIVE"
        assert result.score == 0.95
        assert result.emoji == "😊"

    def test_valid_negative_sentiment(self) -> None:
        """test valid negative sentiment."""
        result = SentimentResult(label="NEGATIVE", score=0.85, emoji="😞")
        assert result.label == "NEGATIVE"

    def test_valid_neutral_sentiment(self) -> None:
        """test valid neutral sentiment."""
        result = SentimentResult(label="NEUTRAL", score=0.50, emoji="😐")
        assert result.label == "NEUTRAL"

    def test_invalid_label_raises_error(self) -> None:
        """test that invalid label raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SentimentResult(label="HAPPY", score=0.9, emoji="😊")
        assert "label" in str(exc_info.value)

    def test_score_below_zero_raises_error(self) -> None:
        """test that score below 0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SentimentResult(label="POSITIVE", score=-0.1, emoji="😊")
        assert "score" in str(exc_info.value)

    def test_score_above_one_raises_error(self) -> None:
        """test that score above 1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SentimentResult(label="POSITIVE", score=1.5, emoji="😊")
        assert "score" in str(exc_info.value)

    def test_sentiment_is_frozen(self, valid_sentiment_data: dict) -> None:
        """test that SentimentResult is immutable."""
        result = SentimentResult(**valid_sentiment_data)
        with pytest.raises(ValidationError):
            result.label = "NEGATIVE"


class TestTranscriptSegment:
    """tests for TranscriptSegment validation."""

    def test_valid_segment(self, valid_transcript_segment_data: dict) -> None:
        """test valid segment creates successfully."""
        segment = TranscriptSegment(**valid_transcript_segment_data)
        assert segment.text == "Hello, welcome to the show."
        assert segment.speaker == "joe_rogan"
        assert segment.start == 0.0
        assert segment.end == 5.5

    def test_speaker_name_optional(self) -> None:
        """test that speaker_name is optional."""
        segment = TranscriptSegment(
            text="Hello",
            speaker="speaker_01",
            start=0.0,
            end=5.0,
        )
        assert segment.speaker_name is None

    def test_end_before_start_raises_error(
        self, invalid_transcript_segment_data: dict
    ) -> None:
        """test that end before start raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptSegment(**invalid_transcript_segment_data)
        assert "end" in str(exc_info.value).lower()

    def test_negative_start_raises_error(self) -> None:
        """test that negative start raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptSegment(
                text="Hello",
                speaker="speaker_01",
                start=-1.0,
                end=5.0,
            )
        assert "start" in str(exc_info.value).lower()

    def test_empty_text_raises_error(self) -> None:
        """test that empty text raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptSegment(
                text="",
                speaker="speaker_01",
                start=0.0,
                end=5.0,
            )
        assert "text" in str(exc_info.value).lower()


class TestContextEntry:
    """tests for ContextEntry validation."""

    def test_valid_context_entry(self, valid_context_entry_data: dict) -> None:
        """test valid context entry creates successfully."""
        entry = ContextEntry(**valid_context_entry_data)
        assert entry.text == "They visited Paris last summer."
        assert entry.temporal == "early"
        assert entry.sentiment.label == "POSITIVE"

    def test_invalid_temporal_raises_error(self) -> None:
        """test that invalid temporal raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ContextEntry(
                text="Some text",
                speaker="speaker_01",
                temporal="invalid",  # must be early/middle/late
                timestamp=10.0,
                sentiment={"label": "NEUTRAL", "score": 0.5, "emoji": "😐"},
            )
        assert "temporal" in str(exc_info.value).lower()

    def test_optional_fields(self) -> None:
        """test that optional fields work."""
        entry = ContextEntry(
            text="Some text",
            speaker="speaker_01",
            temporal="middle",
            timestamp=10.0,
            sentiment={"label": "NEUTRAL", "score": 0.5, "emoji": "😐"},
        )
        assert entry.person is None


class TestSerializedEdge:
    """tests for SerializedEdge validation."""

    def test_valid_edge(self) -> None:
        """test valid edge creates successfully."""
        edge = SerializedEdge(
            source="John Smith",
            target="Paris",
            weight=3,
            relation="mentioned_in",
            speakers=["joe_rogan"],
            contexts=[],
        )
        assert edge.source == "John Smith"
        assert edge.weight == 3

    def test_weight_must_be_positive(self) -> None:
        """test that weight must be >= 1."""
        with pytest.raises(ValidationError) as exc_info:
            SerializedEdge(
                source="John",
                target="Paris",
                weight=0,
                relation="mentioned_in",
                speakers=[],
                contexts=[],
            )
        assert "weight" in str(exc_info.value).lower()

    def test_defaults_work(self) -> None:
        """test that defaults are applied."""
        edge = SerializedEdge(
            source="John",
            target="Paris",
        )
        assert edge.weight == 1
        assert edge.speakers == []
        assert edge.contexts == []

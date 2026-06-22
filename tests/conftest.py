"""shared pytest fixtures for podcast_graphs tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def valid_transcript_segment_data() -> dict:
    """valid transcript segment as dict."""
    return {
        "text": "Hello, welcome to the show.",
        "speaker": "joe_rogan",
        "speaker_name": "Joe Rogan",
        "start": 0.0,
        "end": 5.5,
    }


@pytest.fixture
def valid_sentiment_data() -> dict:
    """valid sentiment result as dict."""
    return {
        "label": "POSITIVE",
        "score": 0.95,
        "emoji": "😊",
    }


@pytest.fixture
def valid_context_entry_data() -> dict:
    """valid context entry as dict."""
    return {
        "text": "They visited Paris last summer.",
        "speaker": "guest_01",
        "temporal": "early",
        "timestamp": 120.5,
        "sentiment": {
            "label": "POSITIVE",
            "score": 0.85,
            "emoji": "😊",
        },
        "person": "John Smith",
    }


@pytest.fixture
def valid_transcript_file_data(valid_transcript_segment_data: dict) -> dict:
    """valid complete transcript file as dict."""
    return {
        "audio_file": "episode_001.mp3",
        "language": "en",
        "segments": [valid_transcript_segment_data],
    }


@pytest.fixture
def invalid_transcript_segment_data() -> dict:
    """invalid transcript segment - end before start."""
    return {
        "text": "Hello",
        "speaker": "speaker_01",
        "start": 10.0,
        "end": 5.0,  # end before start - invalid
    }

"""Sentiment analysis using DistilBERT.

Provides lazy-loaded sentiment analysis with a singleton model instance.
"""

from __future__ import annotations

import logging
from typing import Any

from podcast_graphs.constants import SENTIMENT_EMOJI
from podcast_graphs.types import SentimentResult

logger = logging.getLogger(__name__)

_sentiment_analyzer: Any | None = None


def get_sentiment_analyzer() -> Any:
    """Get or initialize the sentiment analysis pipeline."""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        logger.info("Loading sentiment analysis model...")
        from transformers import pipeline

        _sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model="distilbert/distilbert-base-uncased-finetuned-sst-2-english",
            device=-1,
        )
    return _sentiment_analyzer


def analyze_sentiment(text: str) -> SentimentResult:
    """Analyze sentiment of a text snippet.

    Returns a SentimentResult with label (POSITIVE/NEGATIVE/NEUTRAL),
    score (confidence), and emoji.
    """
    if not text or len(text.strip()) < 10:
        return SentimentResult(label="NEUTRAL", score=0.0, emoji="😐")

    try:
        analyzer = get_sentiment_analyzer()
        result = analyzer(text[:512])[0]
        return SentimentResult(
            label=result["label"],
            score=result["score"],
            emoji=SENTIMENT_EMOJI.get(result["label"], "😐"),
        )
    except Exception as e:
        logger.warning("Sentiment analysis failed: %s", e)
        return SentimentResult(label="NEUTRAL", score=0.0, emoji="😐")

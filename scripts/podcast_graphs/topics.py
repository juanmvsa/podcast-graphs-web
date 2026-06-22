"""BERTopic-based episode topic clustering.

Clusters podcast episodes into topics using sentence embeddings
and provides text preprocessing for topic modeling.
"""

from __future__ import annotations

import logging
import re

from podcast_graphs.constants import SPEECH_FILLER_PHRASES, SPEECH_FILLERS
from podcast_graphs.types import (
    EpisodeClusterInput,
    TopicResults,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)


def prepare_topic_document(
    segments: list[TranscriptSegment],
    min_segment_words: int = 15,
) -> str:
    """Prepare a single episode's transcript for topic modeling.

    Filters out short segments, strips speech fillers, and returns
    cleaned text suitable for BERTopic.
    """
    filler_pattern = re.compile(
        r"\b(" + "|".join(re.escape(p) for p in SPEECH_FILLER_PHRASES) + r")\b",
        re.IGNORECASE,
    )
    filler_words_pattern = re.compile(
        r"\b(" + "|".join(re.escape(w) for w in SPEECH_FILLERS) + r")\b",
        re.IGNORECASE,
    )

    cleaned_segments: list[str] = []
    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue
        if len(text.split()) < min_segment_words:
            continue

        text = filler_pattern.sub("", text)
        text = filler_words_pattern.sub("", text)
        text = re.sub(r"\s+", " ", text).strip()

        if len(text.split()) >= min_segment_words:
            cleaned_segments.append(text)

    return " ".join(cleaned_segments)


def compute_topic_diversity(
    topics_summary: list[dict[str, object]],
    top_n: int = 10,
) -> float:
    """Compute topic diversity: fraction of unique words across all topics.

    A score of 1.0 means every topic uses completely different words.
    """
    if not topics_summary:
        return 0.0

    all_words: list[str] = []
    for topic in topics_summary:
        words = topic.get("topic_words", [])[:top_n]
        all_words.extend(words)

    if not all_words:
        return 0.0

    return len(set(all_words)) / len(all_words)


def cluster_episode_topics(
    episodes_data: list[EpisodeClusterInput],
    min_topic_size: int = 2,
    nr_topics: int | None = None,
) -> TopicResults:
    """Cluster episodes by topics using BERTopic.

    Args:
        episodes_data: list of dicts with 'name', 'text', and optionally 'show' keys
        min_topic_size: minimum number of documents per topic
        nr_topics: number of topics to extract (None = auto)

    Returns:
        TopicResults dict with 'topics', 'episode_topics', 'topic_info', and 'metrics'
    """
    if len(episodes_data) < min_topic_size:
        logger.warning(
            "Not enough episodes (%d) for topic clustering", len(episodes_data)
        )
        return TopicResults(
            topics=[], episode_topics={}, topic_info=[], metrics={}
        )

    try:
        from bertopic import BERTopic
        from bertopic.representation import KeyBERTInspired
        from sentence_transformers import SentenceTransformer
        from sklearn.feature_extraction.text import CountVectorizer

        logger.info("Clustering %d episodes into topics...", len(episodes_data))

        texts = [ep["text"] for ep in episodes_data]
        names = [ep["name"] for ep in episodes_data]

        embedding_model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        vectorizer = CountVectorizer(
            stop_words="english",
            min_df=2,
            max_df=0.9,
            ngram_range=(1, 2),
        )
        representation_model = KeyBERTInspired()

        topic_model = BERTopic(
            embedding_model=embedding_model,
            vectorizer_model=vectorizer,
            representation_model=representation_model,
            min_topic_size=min_topic_size,
            nr_topics=nr_topics,
            top_n_words=10,
            calculate_probabilities=False,
            verbose=False,
        )

        topics, _probabilities = topic_model.fit_transform(texts)
        topic_info = topic_model.get_topic_info()

        # build episode -> topic mapping
        episode_topics: dict[str, dict[str, object]] = {}
        for name, topic_id in zip(names, topics):
            if topic_id != -1:
                topic_words = topic_model.get_topic(topic_id)
                top_words = (
                    [word for word, _ in topic_words[:5]] if topic_words else []
                )
                episode_topics[name] = {
                    "topic_id": int(topic_id),
                    "topic_words": top_words,
                    "topic_label": (
                        ", ".join(top_words[:3]) if top_words else f"Topic {topic_id}"
                    ),
                }

        # build topic summaries
        topics_summary: list[dict[str, object]] = []
        for _, row in topic_info.iterrows():
            topic_id = int(row["Topic"])
            if topic_id == -1:
                continue

            topic_words = topic_model.get_topic(topic_id)
            top_words = (
                [word for word, _ in topic_words[:10]] if topic_words else []
            )

            episodes_in_topic = [
                name
                for name, data in episode_topics.items()
                if data["topic_id"] == topic_id
            ]

            representative_docs: list[dict[str, str]] = []
            for ep_name in episodes_in_topic[:3]:
                ep_data = next(
                    (ep for ep in episodes_data if ep["name"] == ep_name), None
                )
                if ep_data:
                    excerpt = ep_data["text"][:300].rsplit(" ", 1)[0] + "..."
                    representative_docs.append(
                        {"episode": ep_name, "excerpt": excerpt}
                    )

            topics_summary.append({
                "topic_id": topic_id,
                "topic_words": top_words,
                "topic_label": (
                    ", ".join(top_words[:3]) if top_words else f"Topic {topic_id}"
                ),
                "episode_count": len(episodes_in_topic),
                "episodes": episodes_in_topic,
                "representative_docs": representative_docs,
            })

        # compute quality metrics
        num_outliers = sum(1 for t in topics if t == -1)
        diversity = compute_topic_diversity(topics_summary)

        metrics = {
            "num_topics": len(topics_summary),
            "num_outlier_episodes": num_outliers,
            "total_episodes": len(episodes_data),
            "topic_diversity": round(diversity, 3),
        }

        logger.info(
            "Identified %d topics across %d episodes (diversity=%.2f, outliers=%d)",
            len(topics_summary),
            len(episode_topics),
            diversity,
            num_outliers,
        )

        return TopicResults(
            topics=topics_summary,
            episode_topics=episode_topics,
            topic_info=(
                topic_info.to_dict(orient="records") if not topic_info.empty else []
            ),
            metrics=metrics,
        )

    except Exception as e:
        logger.error("Topic clustering failed: %s", e)
        return TopicResults(
            topics=[], episode_topics={}, topic_info=[], metrics={}
        )

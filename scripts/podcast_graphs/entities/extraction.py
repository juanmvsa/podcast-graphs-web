"""spaCy-based named entity extraction.

Extracts PERSON and PLACE entities from transcript segments using spaCy NER,
with batched inference via nlp.pipe() for performance.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from podcast_graphs.constants import (
    MAX_SEGMENT_TEXT,
    NLP_PIPE_BATCH_SIZE,
    PLACE_LABELS,
)
from podcast_graphs.entities.filtering import (
    canonicalize_place,
    is_garbage_entity,
    normalize_entity,
)
from podcast_graphs.entities.resolution import (
    apply_name_resolution,
    resolve_abbreviation_variants,
    resolve_partial_names,
    resolve_place_duplicates,
)
from podcast_graphs.types import EntityResult, SegmentEntities, TranscriptSegment

if TYPE_CHECKING:
    import spacy

logger = logging.getLogger(__name__)


def extract_entities_from_doc(
    doc: spacy.tokens.Doc,
) -> tuple[set[str], set[str]]:
    """Extract PERSON and PLACE entities from a pre-processed spaCy doc."""
    persons: set[str] = set()
    places: set[str] = set()
    for ent in doc.ents:
        normalized = normalize_entity(ent.text)
        if ent.label_ == "PERSON":
            if is_garbage_entity(normalized, "PERSON"):
                continue
            persons.add(normalized)
        elif ent.label_ in PLACE_LABELS:
            if is_garbage_entity(normalized, "PLACE"):
                continue
            normalized = canonicalize_place(normalized)
            places.add(normalized)
    return persons, places


def extract_episode_entities(
    nlp: spacy.Language,
    segments: list[TranscriptSegment],
    global_person_resolution: dict[str, str] | None = None,
    global_place_resolution: dict[str, str] | None = None,
    global_person_blocklist: set[str] | None = None,
    global_place_blocklist: set[str] | None = None,
) -> EntityResult:
    """Extract entities from all segments in an episode.

    Returns an EntityResult with unique persons and places, plus per-segment
    entity associations for graph construction. Resolves partial names,
    abbreviation variants, and place duplicates.

    Uses nlp.pipe() for batched inference for performance.
    """
    all_persons: set[str] = set()
    all_places: set[str] = set()
    segment_entities: list[SegmentEntities] = []

    # collect non-empty segments and their texts for batched NER
    valid_segments: list[tuple[int, TranscriptSegment]] = []
    texts: list[str] = []
    for seg_idx, segment in enumerate(segments):
        text = segment.get("text", "")
        if not text.strip():
            continue
        valid_segments.append((seg_idx, segment))
        texts.append(text)

    # batch NER with nlp.pipe()
    for (seg_idx, segment), doc in zip(
        valid_segments,
        nlp.pipe(texts, batch_size=NLP_PIPE_BATCH_SIZE),
    ):
        persons, places = extract_entities_from_doc(doc)
        all_persons.update(persons)
        all_places.update(places)

        text_snippet = segment.get("text", "")[:MAX_SEGMENT_TEXT]
        if len(segment.get("text", "")) > MAX_SEGMENT_TEXT:
            text_snippet += "..."

        segment_entities.append(
            SegmentEntities(
                speaker=segment.get("speaker", ""),
                speaker_name=segment.get("speaker_name", ""),
                persons=sorted(persons),
                places=sorted(places),
                text=text_snippet,
                segment_index=seg_idx,
                timestamp=segment.get("start", 0),
            )
        )

    # build episode-level resolution maps
    person_partial = resolve_partial_names(all_persons)
    person_abbrev = resolve_abbreviation_variants(all_persons)
    person_resolution = {**person_abbrev, **person_partial}

    place_dupes = resolve_place_duplicates(all_places)
    cleaned_places = apply_name_resolution(all_places, place_dupes)
    place_partial = resolve_partial_names(cleaned_places)
    place_abbrev = resolve_abbreviation_variants(cleaned_places)
    place_resolution = {**place_dupes, **place_abbrev, **place_partial}

    # layer global resolution on top
    if global_person_resolution:
        person_resolution = {**person_resolution, **global_person_resolution}
    if global_place_resolution:
        place_resolution = {**place_resolution, **global_place_resolution}

    all_persons = apply_name_resolution(all_persons, person_resolution)
    all_places = apply_name_resolution(all_places, place_resolution)

    # remove globally blocked entities
    if global_person_blocklist:
        all_persons -= global_person_blocklist
    if global_place_blocklist:
        all_places -= global_place_blocklist

    # cross-entity dedup: PERSON takes priority over PLACE
    overlap = all_persons & all_places
    all_places -= overlap

    # apply resolution to per-segment entities
    blocked = (global_person_blocklist or set()) | (global_place_blocklist or set()) | overlap
    for seg in segment_entities:
        seg["persons"] = sorted(
            apply_name_resolution(set(seg["persons"]), person_resolution) - blocked
        )
        resolved_places = apply_name_resolution(set(seg["places"]), place_resolution)
        seg["places"] = sorted(resolved_places - blocked - overlap)

    return EntityResult(
        persons=sorted(all_persons),
        places=sorted(all_places),
        segment_entities=segment_entities,
    )

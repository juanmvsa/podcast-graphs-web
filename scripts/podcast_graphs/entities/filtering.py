"""Entity normalization, validation, and garbage filtering.

Functions to clean entity text, detect misclassified entities,
and canonicalize place abbreviations.
"""

from __future__ import annotations

from podcast_graphs.constants import (
    CONTAINS_DIGIT,
    LEADING_ARTICLE,
    LEADING_NOISE,
    LEADING_PROFANITY,
    MAX_ENTITY_TOKENS,
    MIN_ENTITY_LENGTH,
    MIN_SINGLE_TOKEN_LENGTH,
    NON_ALPHA,
    ORG_AS_PERSON,
    PERSON_STOPWORDS,
    PLACE_ABBREVIATIONS,
    PLACE_STOPWORDS,
    POSSESSIVE_SUFFIX,
    REPEATED_PATTERN,
    TRAILING_JUNK,
)


def normalize_entity(text: str) -> str:
    """Normalize an entity string for consistent matching.

    Strips possessives, leading articles, leading profanity prefixes,
    leading noise words, trailing junk, extra whitespace, and title-cases.
    """
    text = text.strip()
    text = POSSESSIVE_SUFFIX.sub("", text)
    text = LEADING_ARTICLE.sub("", text)
    text = LEADING_PROFANITY.sub("", text)
    text = LEADING_NOISE.sub("", text)
    text = TRAILING_JUNK.sub("", text)
    text = " ".join(text.split()).title()
    return text


def normalize_abbreviation(text: str) -> str:
    """Collapse abbreviation dots and spaces: 'J. K. Rowling' -> 'Jk Rowling'.

    Merges single-letter tokens left after dot removal so that
    'J. K.' and 'J.K.' both normalize to 'Jk'.
    """
    stripped = text.replace(".", "").strip()
    tokens = stripped.split()
    merged: list[str] = []
    buf = ""
    for t in tokens:
        if len(t) == 1 and t.isalpha():
            buf += t
        else:
            if buf:
                merged.append(buf)
                buf = ""
            merged.append(t)
    if buf:
        merged.append(buf)
    return " ".join(merged)


def is_garbage_entity(text: str, entity_type: str = "") -> bool:
    """Return True if the entity is garbage / noise / misclassified."""
    if len(text) < MIN_ENTITY_LENGTH:
        return True
    tokens = text.split()
    if len(tokens) > MAX_ENTITY_TOKENS:
        return True
    if len(tokens) == 1 and len(text) < MIN_SINGLE_TOKEN_LENGTH:
        return True
    # reject heavy repetition
    collapsed = text.replace(" ", "")
    if REPEATED_PATTERN.match(collapsed):
        return True
    # detect repeated-word entities
    if len(tokens) >= 2 and len(set(t.lower() for t in tokens)) < len(tokens):
        return True
    # reject if less than 50% alphabetic characters
    alpha_count = len(NON_ALPHA.sub("", text))
    if alpha_count / max(len(text), 1) < 0.5:
        return True
    # reject entities that contain digits
    if CONTAINS_DIGIT.search(text):
        return True
    # check against stopwords
    lower = text.lower()
    lower_tokens = [t.lower() for t in tokens]
    if entity_type == "PERSON":
        if lower in PERSON_STOPWORDS:
            return True
        if lower in ORG_AS_PERSON:
            return True
        if len(tokens) >= 2:
            for tok in lower_tokens:
                if tok in PERSON_STOPWORDS:
                    return True
        if len(tokens) >= 2 and _contains_org_or_brand(lower):
            return True
    if entity_type == "PLACE":
        if lower in PLACE_STOPWORDS:
            return True
        if _contains_org_or_brand(lower):
            return True
    return False


def _contains_org_or_brand(lower_text: str) -> bool:
    """Check if text contains a known org/brand name as a substring."""
    for org in ORG_AS_PERSON:
        if len(org) >= 4 and org in lower_text and lower_text != org:
            return True
    return False


def canonicalize_place(name: str) -> str:
    """Expand known place abbreviations to canonical forms."""
    lookup = name.lower().strip()
    if lookup in PLACE_ABBREVIATIONS:
        return PLACE_ABBREVIATIONS[lookup]
    no_dots = normalize_abbreviation(lookup)
    if no_dots in PLACE_ABBREVIATIONS:
        return PLACE_ABBREVIATIONS[no_dots]
    return name

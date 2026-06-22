"""Entity name resolution: partial names, abbreviation variants, and place dedup.

Provides functions to build resolution maps that normalize entity names
across episodes for consistency.
"""

from __future__ import annotations

from podcast_graphs.constants import KNOWN_PLACE_MERGES
from podcast_graphs.entities.filtering import canonicalize_place, normalize_abbreviation


def resolve_partial_names(entities: set[str]) -> dict[str, str]:
    """Build a mapping from partial / short names to their longest form.

    For example, if both "Sam" and "Sam Altman" exist, maps "Sam" -> "Sam Altman".
    Only merges when the short form is a single token and appears as the first or
    last token of exactly one longer form.
    """
    sorted_ents = sorted(entities, key=lambda x: -len(x))
    mapping: dict[str, str] = {}

    for ent in sorted_ents:
        tokens = ent.split()
        if len(tokens) != 1:
            continue
        candidates = [
            longer
            for longer in sorted_ents
            if longer != ent and (longer.split()[0] == ent or longer.split()[-1] == ent)
        ]
        if len(candidates) == 1:
            mapping[ent] = candidates[0]

    return mapping


def resolve_abbreviation_variants(entities: set[str]) -> dict[str, str]:
    """Merge abbreviation variants (e.g., 'J.K. Rowling' and 'Jk Rowling').

    Keeps the form with dots as canonical since it's more readable.
    """
    mapping: dict[str, str] = {}
    normalized_groups: dict[str, list[str]] = {}
    for ent in entities:
        key = normalize_abbreviation(ent).lower()
        normalized_groups.setdefault(key, []).append(ent)

    for _key, group in normalized_groups.items():
        if len(group) <= 1:
            continue
        canonical = max(group, key=len)
        for variant in group:
            if variant != canonical:
                mapping[variant] = canonical

    return mapping


def resolve_place_duplicates(places: set[str]) -> dict[str, str]:
    """Merge duplicate places after canonicalization.

    E.g., 'Los Angeles' appears from both 'La' and 'Los Angeles'.
    Also merges 'United States Of America' -> 'United States'.
    """
    mapping: dict[str, str] = {}
    canonical_map: dict[str, str] = {}

    for place in places:
        canon = canonicalize_place(place)
        if canon != place:
            mapping[place] = canon
            canonical_map[canon] = canon
        else:
            canonical_map.setdefault(place, place)

    # merge "X Of Y" into "X" if "X" exists
    remaining = {mapping.get(p, p) for p in places}
    for place in list(remaining):
        if " Of " in place:
            shorter = place.split(" Of ")[0]
            if shorter in remaining and shorter != place:
                mapping[place] = shorter

    # apply known merges
    for variant, canonical in KNOWN_PLACE_MERGES.items():
        if variant in places:
            mapping[variant] = canonical

    return mapping


def apply_name_resolution(
    entities: set[str],
    resolution_map: dict[str, str],
) -> set[str]:
    """Replace partial names with their resolved full forms."""
    return {resolution_map.get(e, e) for e in entities}


def close_resolution_map(resolution: dict[str, str]) -> dict[str, str]:
    """Make a resolution map transitive.

    If A → B and B → C, ensures A → C. Prevents chains like
    'Jk Rowling' → 'J.K. Rowling' → 'J. K. Rowling' from leaving
    intermediate forms unresolved.
    """
    changed = True
    while changed:
        changed = False
        for key, val in list(resolution.items()):
            if val in resolution and resolution[val] != val:
                resolution[key] = resolution[val]
                changed = True
    return resolution

"""Wikipedia-based entity disambiguation.

Resolves ambiguous person entities by querying the Wikipedia API to find
canonical full names and map all variants to them.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from podcast_graphs.constants import WIKIPEDIA_PERSON_INDICATORS, WIKIPEDIA_USER_AGENT
from podcast_graphs.entities.resolution import apply_name_resolution

logger = logging.getLogger(__name__)


def _group_person_candidates(persons: set[str]) -> list[list[str]]:
    """Group person entities that likely refer to the same individual.

    Two entities are grouped when one name is clearly a variant of the other:
    - one entity's tokens are a subset of the other's
    - both share the same last-name token AND at least one is multi-token
    """
    groups: list[set[str]] = []
    assigned: set[str] = set()
    sorted_persons = sorted(persons, key=lambda x: -len(x))

    for person in sorted_persons:
        if person in assigned:
            continue
        tokens = set(person.split())
        group = {person}

        for other in sorted_persons:
            if other == person or other in assigned:
                continue
            other_tokens = set(other.split())

            # subset check
            if tokens.issubset(other_tokens) or other_tokens.issubset(tokens):
                group.add(other)
                continue

            # shared surname
            p_list = person.split()
            o_list = other.split()
            if len(p_list) >= 2 and len(o_list) >= 2:
                if p_list[-1] == o_list[-1] and len(p_list[-1]) > 2:
                    group.add(other)

        if len(group) > 1:
            groups.append(group)
            assigned.update(group)

    return [list(g) for g in groups]


def resolve_persons_via_wikipedia(
    persons: set[str],
    existing_resolution: dict[str, str],
    cache_path: Path | None = None,
) -> dict[str, str]:
    """Resolve ambiguous person entities using Wikipedia.

    For groups of person entities that share name tokens, queries Wikipedia
    to find the canonical full name and maps all variants to it.

    Results are cached to disk to avoid redundant API calls across runs.
    """
    try:
        import wikipediaapi
    except ImportError:
        logger.warning("wikipedia-api not installed; skipping Wikipedia disambiguation")
        return {}

    # apply existing resolutions to see what's already handled
    resolved = apply_name_resolution(persons, existing_resolution)
    already_mapped = set(existing_resolution.keys())

    candidates = _group_person_candidates(resolved)
    if not candidates:
        return {}

    # filter out groups that are fully resolved already
    unresolved_groups: list[list[str]] = []
    for group in candidates:
        unmapped = [p for p in group if p not in already_mapped]
        if len(unmapped) >= 2 or (len(group) >= 2 and len(unmapped) >= 1):
            unresolved_groups.append(group)

    if not unresolved_groups:
        return {}

    # load disk cache
    disk_cache: dict[str, str | None] = {}
    if cache_path is None:
        cache_path = Path("graphs") / ".wiki_cache.json"
    if cache_path.exists():
        try:
            with cache_path.open() as f:
                disk_cache = json.load(f)
        except Exception:
            disk_cache = {}

    # Suppress verbose per-request INFO logs from the wikipediaapi library
    logging.getLogger("wikipediaapi").setLevel(logging.WARNING)

    wiki = wikipediaapi.Wikipedia(user_agent=WIKIPEDIA_USER_AGENT, language="en")
    resolution: dict[str, str] = {}
    queries_made = 0

    logger.info(
        "Resolving %d ambiguous entity groups via Wikipedia...", len(unresolved_groups)
    )

    for group in unresolved_groups:
        sorted_by_len = sorted(group, key=len, reverse=True)
        canonical: str | None = None

        for candidate in sorted_by_len:
            if candidate in disk_cache:
                if disk_cache[candidate]:
                    canonical = disk_cache[candidate]
                    break
                continue

            page = wiki.page(candidate)
            queries_made += 1
            try:
                exists = page.exists()
            except (KeyError, Exception) as exc:
                logger.warning(
                    "Wikipedia API error for '%s': %s — skipping", candidate, exc
                )
                disk_cache[candidate] = None
                continue

            if exists:
                try:
                    wiki_title = page.title
                    summary_start = page.summary[:300].lower()
                except (KeyError, Exception) as exc:
                    logger.warning(
                        "Wikipedia API error reading '%s': %s — skipping",
                        candidate, exc,
                    )
                    disk_cache[candidate] = None
                    continue

                is_person = any(
                    ind in summary_start for ind in WIKIPEDIA_PERSON_INDICATORS
                )
                if is_person:
                    canonical = wiki_title
                    disk_cache[candidate] = canonical
                    break
                else:
                    disk_cache[candidate] = None
            else:
                disk_cache[candidate] = None

        if canonical:
            for variant in group:
                if variant != canonical:
                    resolution[variant] = canonical
            logger.debug("  Wikipedia: %s → %s", group, canonical)

    # persist cache to disk
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with cache_path.open("w") as f:
            json.dump(disk_cache, f, indent=2)
    except Exception as e:
        logger.warning("Could not save Wikipedia cache: %s", e)

    if resolution:
        logger.info(
            "  Wikipedia resolved %d entity variants (%d API queries, %d cached)",
            len(resolution),
            queries_made,
            len(disk_cache),
        )

    return resolution

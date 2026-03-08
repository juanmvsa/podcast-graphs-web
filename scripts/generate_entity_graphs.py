#!/usr/bin/env python3
"""
named entity recognition and movement graph generation for podcast transcripts.

extracts PERSON and PLACE entities from speaker-labeled transcripts using spacy,
then builds directed graphs modeling how people move between places. outputs
per-episode graphs and per-show aggregated graphs as adjacency matrices.

entity types:
    - PERSON: named individuals mentioned in the transcript.
    - PLACE: geographic and location entities (spacy GPE, LOC, FAC).

graph structure:
    - nodes: PERSON and PLACE entities.
    - directed edges: model movement of a PERSON from one PLACE to another.
      when a PERSON is associated with consecutive distinct PLACEs, an edge
      is created from the previous PLACE to the next PLACE, attributed to
      that PERSON.

usage:
    # run with default settings.
    uv run scripts/generate_entity_graphs.py

    # process a specific file.
    uv run scripts/generate_entity_graphs.py --input path/to/transcript.json

    # process a specific file with custom output path.
    uv run scripts/generate_entity_graphs.py \\
        --input path/to/transcript.json \\
        --output path/to/output_graph.json

    # process a specific directory.
    uv run scripts/generate_entity_graphs.py --input path/to/transcripts

    # recursively process all subdirectories.
    uv run scripts/generate_entity_graphs.py --input-dir path/to/parent/directory

    # run with custom input/output directories.
    uv run scripts/generate_entity_graphs.py \\
        --transcripts-dir path/to/transcripts \\
        --output-dir graphs

    # process specific shows only.
    uv run scripts/generate_entity_graphs.py \\
        --shows the_daily --shows candace

    # force reprocessing of all files.
    uv run scripts/generate_entity_graphs.py --force
"""

from __future__ import annotations

import json
import logging
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# add src to path for imports.
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
src_dir = project_root / "src"
if src_dir.exists() and str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# add scripts to path for utils import.
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

import click
import networkx as nx
import polars as pl
import spacy
from pyvis.network import Network
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from utils.rich_utils import console, setup_logging

logger = logging.getLogger(__name__)

# spacy entity labels that map to PLACE.
PLACE_LABELS = {"GPE", "LOC", "FAC"}


@dataclass
class EntityResult:
    """named entities extracted from a single episode."""

    persons: list[str] = field(default_factory=list)
    places: list[str] = field(default_factory=list)
    segment_entities: list[dict] = field(default_factory=list)


@dataclass
class EpisodeGraphData:
    """serializable graph data for a single episode."""

    episode: str
    show: str
    persons: list[str]
    places: list[str]
    nodes: list[str]
    adjacency_matrix: list[list[int]]
    edges: list[dict]


@dataclass
class ShowGraphData:
    """serializable graph data for a show (aggregated across episodes)."""

    show: str
    episode_count: int
    persons: list[str]
    places: list[str]
    nodes: list[str]
    adjacency_matrix: list[list[int]]
    edges: list[dict]


# minimum entity length. single-token entities need more chars.
MIN_ENTITY_LENGTH = 3
MIN_SINGLE_TOKEN_LENGTH = 5

# max tokens in a valid entity name (rejects runaway spans).
MAX_ENTITY_TOKENS = 4

# regex patterns for normalization.
_REPEATED_PATTERN = re.compile(r"^(.{1,4})\1{2,}")
_POSSESSIVE_SUFFIX = re.compile(r"['\u2019]s$", re.IGNORECASE)
_LEADING_ARTICLE = re.compile(r"^(?:the|a|an)\s+", re.IGNORECASE)
_LEADING_PROFANITY = re.compile(
    r"^(?:fuck(?:ing)?|shit(?:ty)?|damn(?:ed)?|bloody|freaking)\s+", re.IGNORECASE
)
_LEADING_NOISE = re.compile(
    r"^(?:pro-?|anti-?|not|all|no|find|this|her|his|versus|vs\.?|googling|like|just)\s+",
    re.IGNORECASE,
)
_NON_ALPHA = re.compile(r"[^a-zA-Z]")
_CONTAINS_DIGIT = re.compile(r"\d")
_ABBREVIATION_DOTS = re.compile(r"(?<!\w)([A-Za-z])\.(?=[A-Za-z]\.|\s|$)")
_TRAILING_JUNK = re.compile(r"[,;:!?\.\s]+$")

# common words that spacy misclassifies as person entities.
_PERSON_STOPWORDS = {
    # filler words and interjections.
    "yay",
    "ooh",
    "rah",
    "hey",
    "wow",
    "yo",
    "huh",
    "ugh",
    "hmm",
    "mm-hmm",
    "uh-huh",
    "uh-oh",
    "oops",
    "intro",
    "outro",
    # familial / generic references.
    "mom",
    "dad",
    "god",
    "babe",
    "dude",
    "bro",
    "sis",
    "hon",
    "sir",
    "bruh",
    "bestie",
    "hun",
    "sweetie",
    "buddy",
    "girl",
    "baby",
    "madam",
    "mister",
    "missus",
    "kiddo",
    "hubby",
    "wifey",
    # common nouns / adjectives misclassified.
    "idol",
    "main",
    "push",
    "drag",
    "crow",
    "garb",
    "toad",
    "hiss",
    "huns",
    "turd",
    "hurd",
    "tick",
    "tons",
    "knee",
    "miss",
    "watt",
    "dole",
    "euro",
    "yada",
    "pun",
    "trad",
    "law",
    "mav",
    "shall",
    "pride",
    "beast",
    "krabs",
    "verdict",
    "emoji",
    "jubilee",
    "athlet",
    "athleta",
    "gener",
    "lesbian",
    "lesbians",
    "zionist",
    "zionists",
    "trans",
    "chick",
    # diseases / medical terms.
    "covid",
    "monkeypox",
    "mpox",
    "aids",
    "adhd",
    # zodiac signs.
    "cancer",
    "aries",
    "libra",
    "gemini",
    "virgo",
    "scorpio",
    "pisces",
    "taurus",
    "capricorn",
    "sagittarius",
    "aquarius",
    "leo",
    # generation labels.
    "gen z",
    "gen x",
    "gen alpha",
    "boomer",
    "millennial",
    # religious / cultural terms.
    "shabbat",
    "ramadan",
    "christmas",
    "easter",
    "kwanzaa",
    "judaism",
    "satan",
    "allah",
    # slang / internet culture.
    "hawk tua",
    "stan twitter",
    "pop crave",
    "darvo",
    "lgbtq",
    "lgbtq+",
    "lgbt",
    # fictional / brand that aren't real people.
    "barbie",
    "minnie mouse",
    "minnie",
    # role labels / generic terms.
    "youtuber",
    "tiktoker",
    "influencer",
    "podcaster",
    "wikipedia",
    "rfk jr",
}

# organizations / brands commonly misclassified as PERSON by spacy.
_ORG_AS_PERSON = {
    # social media / tech platforms.
    "twitter",
    "instagram",
    "meta",
    "facebook",
    "google",
    "apple",
    "microsoft",
    "amazon",
    "netflix",
    "spotify",
    "reddit",
    "snapchat",
    "pinterest",
    "linkedin",
    "whatsapp",
    "telegram",
    "signal",
    "discord",
    "slack",
    "zoom",
    "teams",
    "skype",
    "tiktok",
    "youtube",
    "fox",
    "cnn",
    "msnbc",
    "nbc",
    "abc",
    "cbs",
    "hbo",
    "hulu",
    "disney",
    "openai",
    "spacex",
    "tesla",
    "uber",
    "lyft",
    "airbnb",
    "paypal",
    "venmo",
    "shopify",
    "twitch",
    "tumblr",
    "myspace",
    "grindr",
    "blue sky",
    "bluesky",
    "truth social",
    "threads",
    # brands / products / companies.
    "blueland",
    "bud light",
    "bud lights",
    "protein plus",
    "all bud light",
    "no bud light",
    "ticketmaster",
    "coachella",
    "stonewall",
    "oscar mayer",
    "hallmark",
    "shein",
    "postmates",
    # media / organizations / shows.
    "turning point",
    "daily wire",
    "babylon bee",
    "drag race",
    "fox news",
    "breitbart",
    "infowars",
    "morning joe",
    "dance moms",
    "maintenance phase",
    "rehash podcast",
    "politico",
    "teen vogue",
    "bustle",
    "wired",
    "insta",
}

# common place abbreviation expansions.
_PLACE_ABBREVIATIONS = {
    "la": "Los Angeles",
    "l.a.": "Los Angeles",
    "nyc": "New York City",
    "n.y.c.": "New York City",
    "dc": "Washington D.C.",
    "d.c.": "Washington D.C.",
    "us": "United States",
    "u.s.": "United States",
    "usa": "United States",
    "u.s.a.": "United States",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "sf": "San Francisco",
    "s.f.": "San Francisco",
    "philly": "Philadelphia",
}

# non-place concepts that spacy frequently tags as GPE/LOC/FAC.
_PLACE_STOPWORDS = {
    "ai",
    "anyway",
    "apologia",
    "backlash",
    "beatlemania",
    "berserk",
    "biphobia",
    "blackface",
    "blackout",
    "blogging",
    "bottoms",
    "burning",
    "candyland",
    "caucasian",
    "chemophobia",
    "cisphobia",
    "dearest",
    "dysphoria",
    "euphoria",
    "fandom",
    "hashtag",
    "hell",
    "hello",
    "hemophilia",
    "homeland",
    "hysteria",
    "imagine",
    "insane",
    "intro",
    "laboratory",
    "mpox",
    "naked",
    "phobia",
    "propaganda",
    "provax",
    "psycho",
    "puritan",
    "quiet",
    "scientology",
    "transphobia",
    "totally",
    "wonderland",
    "beholden",
    # short garbage / non-place tokens.
    "jew",
    "bud",
    "gay",
    "pov",
    "dah",
    "hrt",
    "nra",
    "q&a",
    "jan",
    "san",
    "ark",
    "zim",
    "f.a",
    "j.k",
    # zodiac / concepts.
    "aries",
    "cancer",
    "libra",
    "gemini",
    "virgo",
    # demonyms and group labels (not places).
    "gazan",
    "swifties",
    "trans athletes",
    # organizations / platforms misclassified as places.
    "reddit",
    "netflix",
    "spotify",
    "grindr",
    "youtube",
    "myspace",
    "blue sky",
    "bluesky",
    "daily wire",
    "drag race",
    "ticketmaster",
    "teen vogue",
    "bustle",
    "wired",
    "blueland",
    "shopify",
    "truth social",
    "threads",
    "spacex",
    "openai",
    "pinterest",
    "hinge",
    "babylon bee",
    # generic / vague terms.
    "vantage",
    "overton",
    "pride",
    "homo sapiens",
    "ozempic",
    "satan",
    "kool-aid",
    "speedo",
    # person names misclassified as places.
    "paris hilton",
    "kid rock",
    "rock hudson",
    "cam dallas",
    "asia jackson",
    "zendaya",
    # brand/product/show names misclassified as places.
    "protein plus",
    "bud light",
    "coachella",
    "comedy central",
    "craigslist",
    "met gala",
    "party city",
    "louis vuitton",
    "alibaba",
    "postmates",
    "tumblr",
    "oasis",
    "zynga",
    "young turks",
    "skyhorse",
    # compound garbage that look like place but aren't.
    "point usa",
    "ac la",
    "gen alpha",
    "anti-israel",
    "pro-israel",
    "anti-black",
    "anti-lgbt",
    "new black",
    "new photo",
    "red states",
    "jubilee overton",
    "trading spaces",
    "dream tour",
    "velvet glove cast",
    "kamala hq",
    "america fest",
    "broadway deschanel",
    "yellow king",
    "moon lander",
    "highways",
    "easter",
    "juneteenth",
    "purim",
    "intifada",
    "wi-fi",
    "tic tacs",
}


def normalize_entity(text: str) -> str:
    """normalize an entity string for consistent matching.

    strips possessives, leading articles, leading profanity prefixes,
    leading noise words, trailing junk, extra whitespace, and title-cases.
    """
    text = text.strip()
    # strip possessives.
    text = _POSSESSIVE_SUFFIX.sub("", text)
    # strip leading articles.
    text = _LEADING_ARTICLE.sub("", text)
    # strip leading profanity (e.g., "Fuck Blair White" -> "Blair White").
    text = _LEADING_PROFANITY.sub("", text)
    # strip leading noise words (e.g., "Pro-Donald Trump" -> "Donald Trump").
    text = _LEADING_NOISE.sub("", text)
    # strip trailing punctuation / junk.
    text = _TRAILING_JUNK.sub("", text)
    # collapse whitespace and title-case.
    text = " ".join(text.split()).title()
    return text


def normalize_abbreviation(text: str) -> str:
    """collapse abbreviation dots: 'J.K.' -> 'Jk', 'U.S.' -> 'Us'."""
    return text.replace(".", "").replace(" ", " ").strip()


def is_garbage_entity(text: str, entity_type: str = "") -> bool:
    """return True if the entity is garbage / noise / misclassified."""
    if len(text) < MIN_ENTITY_LENGTH:
        return True
    tokens = text.split()
    # reject overly long entity spans (spacy runaway).
    if len(tokens) > MAX_ENTITY_TOKENS:
        return True
    # single-token entities need more characters to be trustworthy.
    if len(tokens) == 1 and len(text) < MIN_SINGLE_TOKEN_LENGTH:
        return True
    # reject heavy repetition (e.g., "Grà Grà Grà..." or "Athlet Athlet").
    collapsed = text.replace(" ", "")
    if _REPEATED_PATTERN.match(collapsed):
        return True
    # detect repeated-word entities (e.g., "Athlet Athlet", "Gener La Gener La").
    if len(tokens) >= 2 and len(set(t.lower() for t in tokens)) < len(tokens):
        return True
    # reject if less than 50% alphabetic characters.
    alpha_count = len(_NON_ALPHA.sub("", text))
    if alpha_count / max(len(text), 1) < 0.5:
        return True
    # reject entities that contain digits (e.g., "Bill 4440", "Trump 2028").
    if _CONTAINS_DIGIT.search(text):
        return True
    # check against stopwords (case-insensitive), including token-level matches.
    lower = text.lower()
    lower_tokens = [t.lower() for t in tokens]
    if entity_type == "PERSON":
        if lower in _PERSON_STOPWORDS:
            return True
        if lower in _ORG_AS_PERSON:
            return True
        # reject multi-word entities where any token is a person stopword.
        # this catches "Lesbian Camp", "Christian Zionist", etc.
        if len(tokens) >= 2:
            for tok in lower_tokens:
                if tok in _PERSON_STOPWORDS:
                    return True
        # reject compound entities that contain org/brand names as substrings.
        if len(tokens) >= 2 and _contains_org_or_brand(lower):
            return True
    if entity_type == "PLACE":
        if lower in _PLACE_STOPWORDS:
            return True
        # reject places that contain org/brand names.
        if _contains_org_or_brand(lower):
            return True
    return False


def _contains_org_or_brand(lower_text: str) -> bool:
    """check if text contains a known org/brand name as a substring."""
    all_orgs = _ORG_AS_PERSON | {
        "blueland",
        "bud light",
        "youtube",
        "instagram",
        "spotify",
        "netflix",
        "reddit",
        "tiktok",
        "facebook",
    }
    for org in all_orgs:
        if len(org) >= 4 and org in lower_text and lower_text != org:
            return True
    return False


def canonicalize_place(name: str) -> str:
    """expand known place abbreviations to canonical forms."""
    lookup = name.lower().strip()
    # try with and without dots.
    if lookup in _PLACE_ABBREVIATIONS:
        return _PLACE_ABBREVIATIONS[lookup]
    no_dots = normalize_abbreviation(lookup)
    if no_dots in _PLACE_ABBREVIATIONS:
        return _PLACE_ABBREVIATIONS[no_dots]
    return name


def resolve_partial_names(entities: set[str]) -> dict[str, str]:
    """build a mapping from partial / short names to their longest form.

    for example, if both "Sam" and "Sam Altman" exist, maps "Sam" -> "Sam Altman".
    only merges when the short form is a single token and appears as the first or
    last token of exactly one longer form.
    """
    sorted_ents = sorted(entities, key=lambda x: -len(x))
    mapping: dict[str, str] = {}

    for ent in sorted_ents:
        tokens = ent.split()
        if len(tokens) != 1:
            continue
        # single-token name: look for a longer form that starts or ends with it.
        candidates = [
            longer
            for longer in sorted_ents
            if longer != ent and (longer.split()[0] == ent or longer.split()[-1] == ent)
        ]
        if len(candidates) == 1:
            mapping[ent] = candidates[0]

    return mapping


def resolve_abbreviation_variants(entities: set[str]) -> dict[str, str]:
    """merge abbreviation variants (e.g., 'J.K. Rowling' and 'Jk Rowling').

    keeps the form with dots as canonical since it's more readable.
    """
    mapping: dict[str, str] = {}
    normalized_groups: dict[str, list[str]] = {}
    for ent in entities:
        key = normalize_abbreviation(ent).lower()
        normalized_groups.setdefault(key, []).append(ent)

    for key, group in normalized_groups.items():
        if len(group) <= 1:
            continue
        # prefer the longest form (usually has dots or full expansion).
        canonical = max(group, key=len)
        for variant in group:
            if variant != canonical:
                mapping[variant] = canonical

    return mapping


def resolve_place_duplicates(places: set[str]) -> dict[str, str]:
    """merge duplicate places after canonicalization.

    e.g., 'Los Angeles' appears from both 'La' and 'Los Angeles'.
    also merges 'United States Of America' -> 'United States'.
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

    # merge "X Of Y" into "X" if "X" exists (e.g., "United States Of America").
    remaining = {mapping.get(p, p) for p in places}
    for place in list(remaining):
        if " Of " in place:
            shorter = place.split(" Of ")[0]
            if shorter in remaining and shorter != place:
                mapping[place] = shorter

    # explicit known place merges.
    _known_merges = {
        "United States Of America": "United States",
        "Midwestern United States": "United States",
        "United States Supreme Court": "United States",
        "America": "United States",
        "New York State": "New York",
        "Big Palestine": "Palestine",
        "New Israel": "Israel",
        "San Francisco Bay Area": "San Francisco",
        "San Francisco State University": "San Francisco",
        "San Francisco Pride": "San Francisco",
        "Tel Aviv Pride": "Tel Aviv",
        "Miami Dade County": "Miami",
        "Dade County": "Miami",
        "Baltimore County": "Baltimore",
        "Casper Wyoming": "Wyoming",
    }
    for variant, canonical in _known_merges.items():
        if variant in places:
            mapping[variant] = canonical

    return mapping


def apply_name_resolution(
    entities: set[str],
    resolution_map: dict[str, str],
) -> set[str]:
    """replace partial names with their resolved full forms."""
    return {resolution_map.get(e, e) for e in entities}


# default batch size for nlp.pipe(). tuned for en_core_web_lg on apple silicon
# where larger batches amortize per-call overhead in the tok2vec component.
_NLP_PIPE_BATCH_SIZE = 256


def extract_entities_from_doc(doc: spacy.tokens.Doc) -> tuple[set[str], set[str]]:
    """extract PERSON and PLACE entities from a pre-processed spacy doc."""
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
            # canonicalize place abbreviations immediately.
            normalized = canonicalize_place(normalized)
            places.add(normalized)
    return persons, places


def extract_episode_entities(
    nlp: spacy.Language,
    segments: list[dict],
    global_person_resolution: dict[str, str] | None = None,
    global_place_resolution: dict[str, str] | None = None,
    global_person_blocklist: set[str] | None = None,
    global_place_blocklist: set[str] | None = None,
) -> EntityResult:
    """extract entities from all segments in an episode.

    returns an EntityResult with unique persons and places, plus per-segment
    entity associations for graph construction. resolves partial names,
    abbreviation variants, and place duplicates.

    uses nlp.pipe() for batched inference, which is significantly faster than
    calling nlp() on each segment individually.

    if global resolution maps are provided, applies them after episode-level
    resolution for cross-episode consistency.
    """
    all_persons: set[str] = set()
    all_places: set[str] = set()
    segment_entities: list[dict] = []

    # collect non-empty segments and their texts for batched NER.
    valid_segments: list[tuple[int, dict]] = []
    texts: list[str] = []
    for seg_idx, segment in enumerate(segments):
        text = segment.get("text", "")
        if not text.strip():
            continue
        valid_segments.append((seg_idx, segment))
        texts.append(text)

    # batch NER with nlp.pipe().
    for (seg_idx, segment), doc in zip(
        valid_segments,
        nlp.pipe(texts, batch_size=_NLP_PIPE_BATCH_SIZE),
    ):
        persons, places = extract_entities_from_doc(doc)
        all_persons.update(persons)
        all_places.update(places)

        # truncate text for context snippets (max 200 chars)
        text_snippet = segment.get("text", "")[:200]
        if len(segment.get("text", "")) > 200:
            text_snippet += "..."

        segment_entities.append(
            {
                "speaker": segment.get("speaker", ""),
                "speaker_name": segment.get("speaker_name", ""),
                "persons": sorted(persons),
                "places": sorted(places),
                "text": text_snippet,
                "segment_index": seg_idx,
                "timestamp": segment.get("start", 0),
            }
        )

    # build episode-level resolution maps.
    person_partial = resolve_partial_names(all_persons)
    person_abbrev = resolve_abbreviation_variants(all_persons)
    person_resolution = {**person_abbrev, **person_partial}

    # resolve place duplicates first to clean the set before partial name resolution.
    # this prevents resolve_partial_names from mapping e.g. "Palestine" -> "Big Palestine".
    place_dupes = resolve_place_duplicates(all_places)
    cleaned_places = apply_name_resolution(all_places, place_dupes)
    place_partial = resolve_partial_names(cleaned_places)
    place_abbrev = resolve_abbreviation_variants(cleaned_places)
    place_resolution = {**place_dupes, **place_abbrev, **place_partial}

    # layer global resolution on top (show-level normalization).
    if global_person_resolution:
        person_resolution = {**person_resolution, **global_person_resolution}
    if global_place_resolution:
        place_resolution = {**place_resolution, **global_place_resolution}

    all_persons = apply_name_resolution(all_persons, person_resolution)
    all_places = apply_name_resolution(all_places, place_resolution)

    # remove globally blocked entities.
    if global_person_blocklist:
        all_persons -= global_person_blocklist
    if global_place_blocklist:
        all_places -= global_place_blocklist

    # cross-entity dedup: if an entity is tagged as both PERSON and PLACE,
    # keep it only as PERSON (spacy PERSON label is more reliable).
    overlap = all_persons & all_places
    all_places -= overlap

    # apply resolution to per-segment entities.
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


def build_episode_graph(entity_result: EntityResult) -> nx.DiGraph:
    """build a directed graph from episode entity data.

    tracks person-place associations across segments. when a person appears
    with different places in successive mentions, a directed edge is created
    from the previous place to the new place, with the person as an attribute.

    enhanced with narrative context including text snippets, speaker attribution,
    and temporal markers.
    """
    graph = nx.DiGraph()

    # add all entities as nodes with type attribute.
    for person in entity_result.persons:
        graph.add_node(person, entity_type="PERSON")
    for place in entity_result.places:
        graph.add_node(place, entity_type="PLACE")

    # track last known place per person to detect movement.
    person_last_place: dict[str, str] = {}

    total_segments = len(entity_result.segment_entities)

    for seg_ents in entity_result.segment_entities:
        persons_in_seg = seg_ents["persons"]
        places_in_seg = seg_ents["places"]
        speaker = seg_ents.get("speaker_name") or seg_ents.get("speaker", "")
        text = seg_ents.get("text", "")
        seg_idx = seg_ents.get("segment_index", 0)
        timestamp = seg_ents.get("timestamp", 0)

        # calculate temporal position (early/mid/late)
        position_pct = (seg_idx / total_segments) * 100 if total_segments > 0 else 0
        if position_pct < 33:
            temporal = "early"
        elif position_pct < 66:
            temporal = "middle"
        else:
            temporal = "late"

        if not places_in_seg:
            continue

        for person in persons_in_seg:
            for place in places_in_seg:
                # create person -> place edge (person is associated with place).
                if graph.has_edge(person, place):
                    edge_data = graph[person][place]
                    edge_data["weight"] += 1
                    # append context if not too many already
                    if len(edge_data.get("contexts", [])) < 3:
                        edge_data.setdefault("contexts", []).append({
                            "text": text,
                            "speaker": speaker,
                            "temporal": temporal,
                            "timestamp": timestamp
                        })
                    # track speakers
                    if speaker and speaker not in edge_data.get("speakers", []):
                        edge_data.setdefault("speakers", []).append(speaker)
                else:
                    graph.add_edge(
                        person,
                        place,
                        weight=1,
                        relation="mentioned_in",
                        contexts=[{
                            "text": text,
                            "speaker": speaker,
                            "temporal": temporal,
                            "timestamp": timestamp
                        }],
                        speakers=[speaker] if speaker else []
                    )

                # detect movement: previous place -> new place via person.
                if person in person_last_place:
                    prev_place = person_last_place[person]
                    if prev_place != place:
                        if graph.has_edge(prev_place, place):
                            edge_data = graph[prev_place][place]
                            edge_data["weight"] += 1
                            travelers = edge_data.get("travelers", [])
                            if person not in travelers:
                                travelers.append(person)
                                edge_data["travelers"] = travelers
                            # append context
                            if len(edge_data.get("contexts", [])) < 3:
                                edge_data.setdefault("contexts", []).append({
                                    "text": text,
                                    "speaker": speaker,
                                    "temporal": temporal,
                                    "timestamp": timestamp,
                                    "person": person
                                })
                            # track speakers
                            if speaker and speaker not in edge_data.get("speakers", []):
                                edge_data.setdefault("speakers", []).append(speaker)
                        else:
                            graph.add_edge(
                                prev_place,
                                place,
                                weight=1,
                                relation="traveled_to",
                                travelers=[person],
                                contexts=[{
                                    "text": text,
                                    "speaker": speaker,
                                    "temporal": temporal,
                                    "timestamp": timestamp,
                                    "person": person
                                }],
                                speakers=[speaker] if speaker else []
                            )

                person_last_place[person] = place

        # also handle segments with places but no named persons:
        # attribute to the speaker if available.
        if not persons_in_seg and places_in_seg:
            speaker_name = seg_ents.get("speaker_name") or seg_ents.get("speaker", "")
            if speaker_name:
                speaker_normalized = normalize_entity(speaker_name)
                if not graph.has_node(speaker_normalized):
                    graph.add_node(speaker_normalized, entity_type="PERSON")
                for place in places_in_seg:
                    if graph.has_edge(speaker_normalized, place):
                        edge_data = graph[speaker_normalized][place]
                        edge_data["weight"] += 1
                        if len(edge_data.get("contexts", [])) < 3:
                            edge_data.setdefault("contexts", []).append({
                                "text": text,
                                "speaker": speaker_name,
                                "temporal": temporal,
                                "timestamp": timestamp
                            })
                    else:
                        graph.add_edge(
                            speaker_normalized,
                            place,
                            weight=1,
                            relation="mentioned_in",
                            contexts=[{
                                "text": text,
                                "speaker": speaker_name,
                                "temporal": temporal,
                                "timestamp": timestamp
                            }],
                            speakers=[speaker_name]
                        )
                    if speaker_normalized in person_last_place:
                        prev_place = person_last_place[speaker_normalized]
                        if prev_place != place:
                            if graph.has_edge(prev_place, place):
                                edge_data = graph[prev_place][place]
                                edge_data["weight"] += 1
                                travelers = edge_data.get("travelers", [])
                                if speaker_normalized not in travelers:
                                    travelers.append(speaker_normalized)
                                    edge_data["travelers"] = travelers
                                if len(edge_data.get("contexts", [])) < 3:
                                    edge_data.setdefault("contexts", []).append({
                                        "text": text,
                                        "speaker": speaker_name,
                                        "temporal": temporal,
                                        "timestamp": timestamp,
                                        "person": speaker_normalized
                                    })
                            else:
                                graph.add_edge(
                                    prev_place,
                                    place,
                                    weight=1,
                                    relation="traveled_to",
                                    travelers=[speaker_normalized],
                                    contexts=[{
                                        "text": text,
                                        "speaker": speaker_name,
                                        "temporal": temporal,
                                        "timestamp": timestamp,
                                        "person": speaker_normalized
                                    }],
                                    speakers=[speaker_name]
                                )
                    person_last_place[speaker_normalized] = place

    return graph


def graph_to_adjacency_matrix(graph: nx.DiGraph) -> tuple[list[str], list[list[int]]]:
    """convert a networkx digraph to an adjacency matrix.

    returns the ordered node list and the matrix as nested lists.
    """
    nodes = sorted(graph.nodes())
    if not nodes:
        return [], []
    # convert sparse matrix to dense array, then to list
    sparse_matrix = nx.adjacency_matrix(graph, nodelist=nodes)
    matrix = sparse_matrix.toarray().tolist()
    return nodes, matrix


def graph_to_polars_adjacency(graph: nx.DiGraph) -> pl.DataFrame:
    """convert a networkx digraph adjacency matrix to a polars dataframe."""
    nodes, matrix = graph_to_adjacency_matrix(graph)
    if not nodes:
        return pl.DataFrame()
    data = {"node": nodes}
    for i, node in enumerate(nodes):
        data[node] = [row[i] for row in matrix]
    return pl.DataFrame(data)


def serialize_graph(
    graph: nx.DiGraph,
    episode: str,
    show: str,
    entity_result: EntityResult,
) -> EpisodeGraphData:
    """serialize a graph to a storable format with adjacency matrix."""
    nodes, matrix = graph_to_adjacency_matrix(graph)
    edges = []
    for u, v, data in graph.edges(data=True):
        edge = {"source": u, "target": v, "weight": data.get("weight", 1)}
        if "relation" in data:
            edge["relation"] = data["relation"]
        if "travelers" in data:
            edge["travelers"] = data["travelers"]
        edges.append(edge)

    return EpisodeGraphData(
        episode=episode,
        show=show,
        persons=entity_result.persons,
        places=entity_result.places,
        nodes=nodes,
        adjacency_matrix=matrix,
        edges=edges,
    )


def merge_graphs(graphs: list[nx.DiGraph]) -> nx.DiGraph:
    """merge multiple directed graphs into a single aggregated graph."""
    merged = nx.DiGraph()
    for g in graphs:
        for node, attrs in g.nodes(data=True):
            if merged.has_node(node):
                pass
            else:
                merged.add_node(node, **attrs)
        for u, v, data in g.edges(data=True):
            if merged.has_edge(u, v):
                merged[u][v]["weight"] = merged[u][v].get("weight", 0) + data.get("weight", 1)
                existing_travelers = merged[u][v].get("travelers", [])
                new_travelers = data.get("travelers", [])
                for t in new_travelers:
                    if t not in existing_travelers:
                        existing_travelers.append(t)
                if existing_travelers:
                    merged[u][v]["travelers"] = existing_travelers
            else:
                merged.add_edge(u, v, **data)
    return merged


# node colors by entity type.
PERSON_COLOR = "#4FC3F7"
PLACE_COLOR = "#FF8A65"
MOVEMENT_EDGE_COLOR = "#AB47BC"
ASSOCIATION_EDGE_COLOR = "#90A4AE"

# minor words that should not be capitalized in titles (unless first/last word).
_TITLE_MINOR_WORDS = {
    "a", "an", "and", "as", "at", "but", "by", "for", "if", "in", "nor",
    "of", "on", "or", "so", "the", "to", "up", "vs", "yet", "with",
}


def humanize_title(snake_text: str) -> str:
    """convert a snake_case string to a human-readable title.

    applies title-case rules: capitalizes major words, lowercases minor words
    (articles, conjunctions, prepositions) unless they are the first or last word.
    """
    words = snake_text.replace("_", " ").split()
    if not words:
        return snake_text

    result = []
    for i, word in enumerate(words):
        if i == 0 or i == len(words) - 1 or word.lower() not in _TITLE_MINOR_WORDS:
            result.append(word.capitalize())
        else:
            result.append(word.lower())
    return " ".join(result)


def _build_enhanced_styles() -> str:
    """build enhanced CSS styles for improved UI/UX."""
    return """
        /* === Breadcrumb Navigation === */
        .breadcrumb-nav {
            background: rgba(26, 26, 46, 0.95);
            padding: 12px 32px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            font-size: 0.9rem;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }

        .breadcrumb-nav a {
            color: #4FC3F7;
            text-decoration: none;
            transition: color 0.2s ease;
        }

        .breadcrumb-nav a:hover {
            color: #ffffff;
        }

        .breadcrumb-separator {
            color: #9e9e9e;
            margin: 0 8px;
        }

        .breadcrumb-current {
            color: #e0e0e0;
        }

        /* === Graph Header === */
        #graph-header {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            padding: 24px 32px 20px;
            border-bottom: 1px solid #333;
        }

        #graph-header h1 {
            margin: 0 0 4px 0;
            font-size: 1.6em;
            font-weight: 600;
            color: #ffffff;
            letter-spacing: -0.02em;
        }

        #graph-header .subtitle {
            margin: 0 0 16px 0;
            font-size: 0.95em;
            color: #9e9e9e;
        }

        .toggle-header {
            display: none;
            cursor: pointer;
            color: #4FC3F7;
            font-size: 0.9em;
            margin-top: 8px;
            user-select: none;
        }

        .header-details {
            display: flex;
            gap: 32px;
            flex-wrap: wrap;
            align-items: flex-start;
            margin-top: 16px;
        }

        .info-box {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 12px 16px;
            min-width: 180px;
        }

        .info-box-title {
            font-size: 0.75em;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #9e9e9e;
            margin-bottom: 8px;
            font-weight: 600;
        }

        .legend-items, .stats-items, .controls-items {
            font-size: 0.85em;
            line-height: 1.8;
        }

        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .legend-dot {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }

        .legend-line {
            display: inline-block;
            width: 20px;
            height: 3px;
            border-radius: 2px;
        }

        .stat-number {
            font-weight: 600;
        }

        .controls-items div {
            color: #bbb;
        }

        /* === Entity Search === */
        .entity-search-container {
            margin: 16px 32px;
        }

        .entity-search {
            width: 100%;
            max-width: 500px;
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.2);
            color: #e0e0e0;
            padding: 10px 16px;
            border-radius: 8px;
            font-size: 0.9rem;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }

        .entity-search:focus {
            outline: none;
            border-color: #4FC3F7;
            background: rgba(255,255,255,0.1);
        }

        .entity-search::placeholder {
            color: #9e9e9e;
        }

        /* === Graph Controls === */
        .graph-controls {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 12px 16px;
            margin: 0 32px 16px;
            display: flex;
            gap: 24px;
            flex-wrap: wrap;
            align-items: center;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }

        .control-group {
            display: flex;
            gap: 8px;
            align-items: center;
            flex-wrap: wrap;
        }

        .control-label {
            color: #9e9e9e;
            font-size: 0.85rem;
            margin-right: 4px;
        }

        .control-button {
            background: rgba(79, 195, 247, 0.2);
            border: 1px solid rgba(79, 195, 247, 0.4);
            color: #4FC3F7;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
            transition: all 0.2s ease;
            font-family: inherit;
        }

        .control-button:hover {
            background: rgba(79, 195, 247, 0.3);
            transform: translateY(-1px);
        }

        .control-button:active {
            transform: translateY(0);
        }

        /* === Loading Overlay === */
        .graph-loading {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(30, 30, 30, 0.95);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            transition: opacity 0.3s ease;
        }

        .graph-loading.hidden {
            opacity: 0;
            pointer-events: none;
        }

        .loading-spinner {
            width: 50px;
            height: 50px;
            border: 4px solid rgba(79, 195, 247, 0.2);
            border-top-color: #4FC3F7;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .loading-text {
            color: #4FC3F7;
            margin-top: 16px;
            font-size: 0.9rem;
        }

        .loading-progress {
            width: 200px;
            height: 4px;
            background: rgba(79, 195, 247, 0.2);
            border-radius: 2px;
            margin-top: 12px;
            overflow: hidden;
        }

        .loading-progress-bar {
            height: 100%;
            background: #4FC3F7;
            width: 0%;
            transition: width 0.3s ease;
        }

        /* === Mobile Responsive === */
        @media (max-width: 768px) {
            .breadcrumb-nav {
                padding: 10px 16px;
                font-size: 0.85rem;
            }

            #graph-header {
                padding: 16px 20px;
            }

            #graph-header h1 {
                font-size: 1.2em;
            }

            .toggle-header {
                display: inline-block;
            }

            .header-details {
                display: none;
                margin-top: 12px;
            }

            .header-details.expanded {
                display: flex;
            }

            .entity-search-container {
                margin: 12px 16px;
            }

            .graph-controls {
                margin: 0 16px 12px;
                padding: 10px 12px;
            }

            .control-group {
                width: 100%;
            }

            .info-box {
                min-width: 140px;
            }

            #mynetwork {
                height: 70vh !important;
                min-height: 300px !important;
            }
        }

        /* === Mobile Touch Enhancements === */
        @media (hover: none) and (pointer: coarse) {
            .control-button {
                padding: 10px 16px;
                font-size: 0.9rem;
            }

            .entity-search {
                font-size: 16px; /* Prevent zoom on iOS */
            }
        }
    """


def _build_enhanced_scripts() -> str:
    """build enhanced JavaScript for improved interactivity."""
    return """
    <script>
        // === Global Variables ===
        let physicsEnabled = true;

        // === Header Toggle (Mobile) ===
        function toggleDetails() {
            const details = document.querySelector('.header-details');
            const toggle = document.querySelector('.toggle-header');
            details.classList.toggle('expanded');
            toggle.textContent = details.classList.contains('expanded')
                ? '▲ Hide Details'
                : '▼ Show Details';
        }

        // === Graph Control Functions ===
        function resetView() {
            if (typeof network !== 'undefined') {
                network.moveTo({ scale: 1, position: {x: 0, y: 0}, animation: true });
            }
        }

        function fitToView() {
            if (typeof network !== 'undefined') {
                network.fit({ animation: true });
            }
        }

        function togglePhysics() {
            if (typeof network !== 'undefined') {
                physicsEnabled = !physicsEnabled;
                network.setOptions({ physics: { enabled: physicsEnabled } });
                document.getElementById('physicsLabel').textContent =
                    physicsEnabled ? 'Pause' : 'Resume';
            }
        }

        function showPersonOnly() {
            if (typeof nodes === 'undefined') return;
            const nodeIds = nodes.getIds();
            nodeIds.forEach(id => {
                const node = nodes.get(id);
                nodes.update({
                    id: id,
                    hidden: node.color !== '#4FC3F7'
                });
            });
        }

        function showPlaceOnly() {
            if (typeof nodes === 'undefined') return;
            const nodeIds = nodes.getIds();
            nodeIds.forEach(id => {
                const node = nodes.get(id);
                nodes.update({
                    id: id,
                    hidden: node.color !== '#FF8A65'
                });
            });
        }

        function showAll() {
            if (typeof nodes === 'undefined') return;
            const nodeIds = nodes.getIds();
            nodeIds.forEach(id => {
                nodes.update({ id: id, hidden: false });
            });
            // Reset search
            document.getElementById('entitySearch').value = '';
        }

        // === Entity Search ===
        function searchEntities(query) {
            if (typeof nodes === 'undefined') return;

            if (!query) {
                showAll();
                return;
            }

            const lowerQuery = query.toLowerCase();
            const nodeIds = nodes.getIds();
            const matchingIds = [];

            nodeIds.forEach(id => {
                const node = nodes.get(id);
                const matches = node.label.toLowerCase().includes(lowerQuery);
                nodes.update({
                    id: id,
                    hidden: !matches,
                    borderWidth: matches ? 3 : 1,
                    color: {
                        background: node.color,
                        border: matches ? '#FFD700' : node.color
                    }
                });
                if (matches) matchingIds.push(id);
            });

            // Focus on matching nodes
            if (matchingIds.length > 0 && typeof network !== 'undefined') {
                network.fit({
                    nodes: matchingIds,
                    animation: true
                });
            }
        }

        // === Loading State Management ===
        document.addEventListener('DOMContentLoaded', function() {
            // Wait for network to be defined
            const checkNetwork = setInterval(function() {
                if (typeof network !== 'undefined') {
                    clearInterval(checkNetwork);

                    // Setup loading progress
                    network.on('stabilizationProgress', function(params) {
                        const progress = Math.round((params.iterations / params.total) * 100);
                        const progressBar = document.getElementById('loadingProgress');
                        const loadingText = document.querySelector('.loading-text');
                        if (progressBar) progressBar.style.width = progress + '%';
                        if (loadingText) loadingText.textContent = `Stabilizing layout... ${progress}%`;
                    });

                    network.on('stabilizationIterationsDone', function() {
                        const loadingText = document.querySelector('.loading-text');
                        if (loadingText) loadingText.textContent = 'Complete!';
                        setTimeout(() => {
                            const loading = document.getElementById('graphLoading');
                            if (loading) loading.classList.add('hidden');
                        }, 300);
                    });

                    // Enable navigation buttons for mobile
                    network.setOptions({
                        interaction: {
                            navigationButtons: window.innerWidth <= 768,
                            keyboard: {
                                enabled: true,
                                bindToWindow: false
                            }
                        }
                    });
                }
            }, 100);
        });

        // === Mobile Touch Enhancements ===
        if ('ontouchstart' in window) {
            window.addEventListener('load', function() {
                const networkDiv = document.getElementById('mynetwork');
                if (networkDiv) {
                    // Prevent pull-to-refresh when panning graph
                    let lastY = 0;
                    networkDiv.addEventListener('touchmove', function(e) {
                        const currentY = e.touches[0].clientY;
                        if (lastY < currentY && window.scrollY === 0) {
                            e.preventDefault();
                        }
                        lastY = currentY;
                    }, { passive: false });

                    // Disable double-tap zoom on network canvas
                    networkDiv.addEventListener('touchstart', function(e) {
                        if (e.touches.length > 1) {
                            e.preventDefault();
                        }
                    }, { passive: false });
                }
            });
        }

        // === Responsive Navigation Buttons ===
        window.addEventListener('resize', function() {
            if (typeof network !== 'undefined') {
                network.setOptions({
                    interaction: {
                        navigationButtons: window.innerWidth <= 768
                    }
                });
            }
        });
    </script>
    """


def _build_legend_html(
    title: str,
    subtitle: str,
    person_count: int,
    place_count: int,
    edge_count: int,
) -> str:
    """build the html header with title, stats, and color legend."""
    return f"""
    <!-- Breadcrumb Navigation -->
    <div class="breadcrumb-nav">
        <a href="../../index.html">🏠 Home</a>
        <span class="breadcrumb-separator">/</span>
        <span class="breadcrumb-current">{subtitle}</span>
        <span class="breadcrumb-separator">/</span>
        <span class="breadcrumb-current">{title}</span>
    </div>

    <!-- Graph Header -->
    <div id="graph-header">
        <h1>{title}</h1>
        <p class="subtitle">{subtitle}</p>
        <span class="toggle-header" onclick="toggleDetails()">
            ▼ Show Details
        </span>

        <div class="header-details">
            <!-- Legend -->
            <div class="info-box">
                <div class="info-box-title">Legend</div>
                <div class="legend-items">
                    <div class="legend-item">
                        <span class="legend-dot" style="background: {PERSON_COLOR};"></span>
                        <span>Person</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-dot" style="background: {PLACE_COLOR};"></span>
                        <span>Place</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-line" style="background: {ASSOCIATION_EDGE_COLOR};"></span>
                        <span>Person ↔ Place</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-line" style="background: {MOVEMENT_EDGE_COLOR};"></span>
                        <span>Place → Place</span>
                    </div>
                </div>
            </div>

            <!-- Stats -->
            <div class="info-box">
                <div class="info-box-title">Stats</div>
                <div class="stats-items">
                    <div><span class="stat-number" style="color: {PERSON_COLOR};">{person_count}</span> people</div>
                    <div><span class="stat-number" style="color: {PLACE_COLOR};">{place_count}</span> places</div>
                    <div><span class="stat-number">{edge_count}</span> connections</div>
                </div>
            </div>

            <!-- Controls -->
            <div class="info-box">
                <div class="info-box-title">Controls</div>
                <div class="controls-items">
                    <div>🖱️ Drag nodes to rearrange</div>
                    <div>🔍 Scroll to zoom in/out</div>
                    <div>💬 Hover for details</div>
                </div>
            </div>
        </div>
    </div>

    <!-- Entity Search -->
    <div class="entity-search-container">
        <input
            type="text"
            class="entity-search"
            id="entitySearch"
            placeholder="🔍 Search entities (people, places)..."
            oninput="searchEntities(this.value)"
        >
    </div>

    <!-- Graph Controls -->
    <div class="graph-controls">
        <div class="control-group">
            <span class="control-label">View:</span>
            <button class="control-button" onclick="resetView()">Reset Zoom</button>
            <button class="control-button" onclick="fitToView()">Fit All</button>
            <button class="control-button" onclick="togglePhysics()">
                <span id="physicsLabel">Pause</span> Physics
            </button>
        </div>

        <div class="control-group">
            <span class="control-label">Filter:</span>
            <button class="control-button" onclick="showPersonOnly()">People Only</button>
            <button class="control-button" onclick="showPlaceOnly()">Places Only</button>
            <button class="control-button" onclick="showAll()">Show All</button>
        </div>
    </div>
    """


def visualize_graph(
    graph: nx.DiGraph,
    output_path: Path,
    title: str = "",
    subtitle: str = "",
) -> None:
    """render an interactive pyvis html visualization of a graph."""
    net = Network(
        height="85vh",  # Responsive height
        width="100%",
        directed=True,
        bgcolor="#1e1e1e",
        font_color="white",
        notebook=False,
    )
    net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=150)

    for node, attrs in graph.nodes(data=True):
        entity_type = attrs.get("entity_type", "UNKNOWN")
        color = PERSON_COLOR if entity_type == "PERSON" else PLACE_COLOR
        size = 15 + graph.degree(node) * 2
        label = node
        hover = f"{node}\nType: {entity_type}\nConnections: {graph.degree(node)}"
        net.add_node(node, label=label, title=hover, color=color, size=min(size, 60))

    for u, v, data in graph.edges(data=True):
        relation = data.get("relation", "")
        weight = data.get("weight", 1)
        travelers = data.get("travelers", [])
        contexts = data.get("contexts", [])
        speakers = data.get("speakers", [])

        # determine edge color based on relation type
        if "traveled" in relation or "movement" in relation:
            color = MOVEMENT_EDGE_COLOR
        else:
            color = ASSOCIATION_EDGE_COLOR

        # build rich tooltip with narrative context
        hover_parts = [
            f"📍 {u} → {v}",
            f"━━━━━━━━━━━━━━━━━━━━",
            f"Relationship: {relation.replace('_', ' ').title()}",
            f"Mentions: {weight}",
        ]

        if travelers:
            hover_parts.append(f"People: {', '.join(travelers)}")

        if speakers:
            hover_parts.append(f"Discussed by: {', '.join(set(speakers))}")

        # add narrative context snippets
        if contexts:
            hover_parts.append(f"\n💬 Context:")
            for idx, ctx in enumerate(contexts[:2], 1):  # limit to 2 examples
                temporal = ctx.get("temporal", "")
                speaker = ctx.get("speaker", "Unknown")
                text = ctx.get("text", "")
                person_ctx = ctx.get("person", "")

                # truncate text if too long
                if len(text) > 120:
                    text = text[:120] + "..."

                hover_parts.append(f"\n[{temporal.upper()}] {speaker}:")
                if person_ctx:
                    hover_parts.append(f"  ({person_ctx})")
                hover_parts.append(f'  "{text}"')

        net.add_edge(u, v, value=weight, color=color, title="\n".join(hover_parts))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    net.save_graph(str(output_path))

    # inject custom header with legend into the generated html.
    person_count = sum(
        1 for _, d in graph.nodes(data=True) if d.get("entity_type") == "PERSON"
    )
    place_count = sum(
        1 for _, d in graph.nodes(data=True) if d.get("entity_type") == "PLACE"
    )
    legend_html = _build_legend_html(
        title=title or "Entity Graph",
        subtitle=subtitle,
        person_count=person_count,
        place_count=place_count,
        edge_count=graph.number_of_edges(),
    )

    # build enhanced CSS styles
    enhanced_styles = _build_enhanced_styles()

    # build enhanced JavaScript
    enhanced_scripts = _build_enhanced_scripts()

    html = output_path.read_text(encoding="utf-8")

    # remove the default pyvis heading.
    html = re.sub(
        r"<center>\s*<h1>.*?</h1>\s*</center>",
        "",
        html,
        flags=re.DOTALL,
    )

    # inject enhanced styles in <head>
    html = html.replace("</style>", f"{enhanced_styles}\n</style>", 1)

    # inject legend and controls after <body> tag.
    html = html.replace("<body>", f"<body>\n{legend_html}", 1)

    # add loading overlay to #mynetwork div
    loading_overlay = """
    <div class="graph-loading" id="graphLoading">
        <div class="loading-spinner"></div>
        <div class="loading-text">Initializing graph...</div>
        <div class="loading-progress">
            <div class="loading-progress-bar" id="loadingProgress"></div>
        </div>
    </div>
    """
    html = html.replace(
        '<div id="mynetwork"',
        '<div id="mynetwork" style="position: relative;">' + loading_overlay + '<div style="width: 100%; height: 100%;"',
        1
    )
    # close the wrapper div before the original closing div
    html = re.sub(
        r'(</div>\s*</body>)',
        r'</div>\1',
        html,
        count=1
    )

    # inject enhanced scripts before </body>
    html = html.replace("</body>", f"{enhanced_scripts}\n</body>", 1)

    # update network container height to responsive
    html = re.sub(
        r'height:\s*\d+px;',
        'height: 85vh; min-height: 400px; max-height: 900px;',
        html
    )

    output_path.write_text(html, encoding="utf-8")


def collect_raw_entities(
    nlp: spacy.Language,
    episode_files: list[Path],
    progress: Progress | None = None,
    task_id: int | None = None,
) -> tuple[set[str], set[str]]:
    """first pass: collect all raw entities across all episodes in a show.

    uses nlp.pipe() for batched inference per episode, which is significantly
    faster than calling nlp() on each segment individually.

    returns aggregated person and place entity sets before cross-episode
    normalization.
    """
    all_persons: set[str] = set()
    all_places: set[str] = set()

    for episode_file in episode_files:
        try:
            with open(episode_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            if progress and task_id is not None:
                progress.advance(task_id)
            continue

        texts = [
            seg.get("text", "")
            for seg in data.get("segments", [])
            if seg.get("text", "").strip()
        ]

        for doc in nlp.pipe(texts, batch_size=_NLP_PIPE_BATCH_SIZE):
            persons, places = extract_entities_from_doc(doc)
            all_persons.update(persons)
            all_places.update(places)

        if progress and task_id is not None:
            progress.advance(task_id)

    return all_persons, all_places


def build_global_resolution_maps(
    all_persons: set[str],
    all_places: set[str],
) -> tuple[dict[str, str], dict[str, str], set[str], set[str]]:
    """build show-level entity resolution maps and blocklists.

    returns (person_resolution, place_resolution, person_blocklist, place_blocklist).
    these maps normalize entities consistently across all episodes in a show.
    """
    # resolve partial names globally (e.g., "Trump" -> "Donald Trump").
    person_partial = resolve_partial_names(all_persons)
    person_abbrev = resolve_abbreviation_variants(all_persons)
    person_resolution = {**person_abbrev, **person_partial}

    place_dupes = resolve_place_duplicates(all_places)
    cleaned_places = apply_name_resolution(all_places, place_dupes)
    place_partial = resolve_partial_names(cleaned_places)
    place_abbrev = resolve_abbreviation_variants(cleaned_places)
    place_resolution = {**place_dupes, **place_abbrev, **place_partial}

    # resolve all names first, then detect cross-entity overlap.
    resolved_persons = apply_name_resolution(all_persons, person_resolution)
    resolved_places = apply_name_resolution(all_places, place_resolution)

    # entities that appear as both PERSON and PLACE get blocked from places.
    overlap = resolved_persons & resolved_places
    place_blocklist = overlap.copy()

    # also block places that share a first or last name token with a known person.
    # this catches cases like "Riley Gaines" as a place when it's actually a person.
    person_full_names = {p for p in resolved_persons if len(p.split()) >= 2}
    person_name_tokens: dict[str, list[str]] = {}
    for person in person_full_names:
        for token in person.split():
            person_name_tokens.setdefault(token, []).append(person)

    for place in list(resolved_places):
        place_tokens = place.split()
        if len(place_tokens) <= 2:
            # check if a place entity is actually a person name (multi-token).
            for person in person_full_names:
                if place == person:
                    place_blocklist.add(place)
                    break
            # check if a single-token place matches a person's name token.
            if len(place_tokens) == 1 and place in person_name_tokens:
                # only block if matching persons exist and the token isn't a common
                # geographic name (e.g., "Jordan", "Israel" are both person and place).
                _common_geo_names = {
                    "Jordan",
                    "Israel",
                    "Georgia",
                    "Virginia",
                    "Carolina",
                    "Charlotte",
                    "Dallas",
                    "Houston",
                    "Jackson",
                    "Madison",
                    "Austin",
                    "Florence",
                    "Hamilton",
                    "Lincoln",
                    "Nelson",
                    "Washington",
                    "Clinton",
                    "Monroe",
                    "Springfield",
                }
                if place not in _common_geo_names:
                    place_blocklist.add(place)

    person_blocklist: set[str] = set()

    return person_resolution, place_resolution, person_blocklist, place_blocklist


def process_episode(
    nlp: spacy.Language,
    transcript_path: Path,
    show_name: str,
    global_person_resolution: dict[str, str] | None = None,
    global_place_resolution: dict[str, str] | None = None,
    global_person_blocklist: set[str] | None = None,
    global_place_blocklist: set[str] | None = None,
) -> tuple[EpisodeGraphData, nx.DiGraph] | None:
    """process a single episode transcript and return graph data."""
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error("failed to read %s: %s", transcript_path, e)
        return None

    segments = data.get("segments", [])
    if not segments:
        logger.warning("no segments in %s", transcript_path.name)
        return None

    episode_name = transcript_path.stem

    entity_result = extract_episode_entities(
        nlp,
        segments,
        global_person_resolution=global_person_resolution,
        global_place_resolution=global_place_resolution,
        global_person_blocklist=global_person_blocklist,
        global_place_blocklist=global_place_blocklist,
    )
    graph = build_episode_graph(entity_result)

    graph_data = serialize_graph(graph, episode_name, show_name, entity_result)
    return graph_data, graph


def save_graph_data(graph_data: EpisodeGraphData | ShowGraphData, output_path: Path) -> None:
    """save graph data as json."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(asdict(graph_data), f, ensure_ascii=False, indent=2)


def save_adjacency_csv(graph: nx.DiGraph, output_path: Path) -> None:
    """save adjacency matrix as csv using polars."""
    df = graph_to_polars_adjacency(graph)
    if df.is_empty():
        return
    csv_path = output_path.with_suffix(".csv")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_csv(csv_path)


@click.command()
@click.option(
    "--input",
    "-i",
    "input_path",
    type=click.Path(path_type=Path),
    help="input file or directory with transcripts (overrides --transcripts-dir).",
)
@click.option(
    "--input-dir",
    "-d",
    "input_dir_path",
    type=click.Path(path_type=Path),
    help="recursively process all subdirectories as shows (overrides --transcripts-dir).",
)
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(path_type=Path),
    help="output file path (overrides --output-dir for single file processing).",
)
@click.option(
    "--transcripts-dir",
    type=click.Path(path_type=Path),
    default=Path("graphs"),
    help="directory with speaker-labeled transcripts.",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path("graphs"),
    help="output directory for graph files.",
)
@click.option(
    "--shows",
    multiple=True,
    help="process only specific shows (can be repeated).",
)
@click.option(
    "--spacy-model",
    type=str,
    default="en_core_web_lg",
    help="spacy model for NER.",
)
@click.option(
    "--force",
    is_flag=True,
    help="force reprocessing of all files.",
)
@click.option(
    "--visualize",
    is_flag=True,
    help="generate interactive pyvis html visualizations.",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="logging level.",
)
def generate_entity_graphs(
    input_path: Path | None,
    input_dir_path: Path | None,
    output_path: Path | None,
    transcripts_dir: Path,
    output_dir: Path,
    shows: tuple[str, ...],
    spacy_model: str,
    force: bool,
    visualize: bool,
    log_level: str,
) -> None:
    """extract PERSON/PLACE entities and generate movement graphs."""
    setup_logging(log_level)

    # track if we're processing a single file
    single_file_mode = False
    single_file_path: Path | None = None
    recursive_mode = False

    # handle input-dir flag for recursive processing (highest priority)
    if input_dir_path:
        input_dir_path = input_dir_path.resolve()
        if not input_dir_path.exists():
            console.print(
                f"[bold red]Error: input directory not found: {input_dir_path}[/bold red]"
            )
            sys.exit(1)

        if not input_dir_path.is_dir():
            console.print(
                f"[bold red]Error: --input-dir must be a directory: {input_dir_path}[/bold red]"
            )
            sys.exit(1)

        transcripts_dir = input_dir_path
        recursive_mode = True
        console.print(f"[dim]Recursive mode: scanning {input_dir_path} for subdirectories[/dim]")

    # handle input path flag (overrides transcripts-dir)
    elif input_path:
        input_path = input_path.resolve()
        if not input_path.exists():
            console.print(
                f"[bold red]Error: input path not found: {input_path}[/bold red]"
            )
            sys.exit(1)

        if input_path.is_file():
            # process single file
            single_file_mode = True
            single_file_path = input_path
            transcripts_dir = input_path.parent
            shows = (input_path.parent.name,)  # use parent directory as show name
        else:
            # input is a directory
            transcripts_dir = input_path

    # handle output path flag
    if output_path:
        output_path = output_path.resolve()
        if not single_file_mode:
            console.print(
                "[bold yellow]Warning: --output flag is only used with single file input. "
                "Using --output-dir for directory processing.[/bold yellow]"
            )
        else:
            # for single file mode, use output_path's directory as output_dir
            output_dir = output_path.parent

    transcripts_dir = transcripts_dir.resolve()
    output_dir = output_dir.resolve()

    if not transcripts_dir.exists():
        console.print(
            f"[bold red]Error: transcripts directory not found: {transcripts_dir}[/bold red]"
        )
        sys.exit(1)

    # load spacy model.
    console.print(f"[bold cyan]Loading spaCy model:[/bold cyan] {spacy_model}")
    try:
        nlp = spacy.load(spacy_model, disable=["parser", "lemmatizer"])
    except OSError:
        console.print(
            f"[bold red]Error: spaCy model '{spacy_model}' not found. "
            f"Install it with: uv run python -m spacy download {spacy_model}[/bold red]"
        )
        sys.exit(1)

    # collect show directories.
    if recursive_mode:
        # recursively find all subdirectories with JSON files
        show_dirs = []
        for root, dirs, files in transcripts_dir.walk():
            # skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            # if this directory contains JSON files, it's a show directory
            if any(f.endswith(".json") for f in files):
                show_dirs.append(Path(root))
        show_dirs = sorted(show_dirs)
        console.print(f"[dim]Found {len(show_dirs)} directories with JSON files[/dim]")
    else:
        # only look at immediate subdirectories
        show_dirs = sorted(
            [d for d in transcripts_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
        )

    if shows:
        show_dirs = [d for d in show_dirs if d.name in shows]

    if not show_dirs:
        console.print("[bold yellow]No show directories found to process.[/bold yellow]")
        return

    console.print(f"[bold cyan]Transcripts dir:[/bold cyan] {transcripts_dir}")
    console.print(f"[bold cyan]Output dir:[/bold cyan]      {output_dir}")
    console.print(f"[bold cyan]Shows:[/bold cyan]           {len(show_dirs)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    summaries_dir = output_dir / "summaries"
    summaries_dir.mkdir(parents=True, exist_ok=True)

    total_episodes = 0
    total_processed = 0
    total_skipped = 0
    total_failed = 0

    for show_dir in show_dirs:
        show_name = show_dir.name
        episode_files = sorted(show_dir.glob("*.json"))

        if not episode_files:
            logger.info("no episodes found for show: %s", show_name)
            continue

        console.print(
            f"\n[bold magenta]Processing show:[/bold magenta] {show_name} "
            f"({len(episode_files)} episodes)"
        )

        show_output_dir = output_dir / show_name
        show_output_dir.mkdir(parents=True, exist_ok=True)

        # --- pass 1: collect all raw entities across the show ---
        console.print("  [dim]Pass 1: collecting entities for global normalization...[/dim]")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"  scan {show_name}", total=len(episode_files))
            show_raw_persons, show_raw_places = collect_raw_entities(
                nlp, episode_files, progress, task
            )

        # build global resolution maps from the full show entity pool.
        g_person_res, g_place_res, g_person_block, g_place_block = build_global_resolution_maps(
            show_raw_persons, show_raw_places
        )
        if g_person_res:
            console.print(f"  [dim]Global person resolutions: {len(g_person_res)}[/dim]")
        if g_place_res:
            console.print(f"  [dim]Global place resolutions: {len(g_place_res)}[/dim]")

        # --- pass 2: process episodes with global normalization ---
        console.print("  [dim]Pass 2: generating graphs with normalized entities...[/dim]")
        show_graphs: list[nx.DiGraph] = []
        show_persons: set[str] = set()
        show_places: set[str] = set()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"  {show_name}", total=len(episode_files))

            for episode_file in episode_files:
                total_episodes += 1
                episode_name = episode_file.stem

                # determine output path (use custom path if in single file mode and specified)
                if single_file_mode and output_path and episode_file == single_file_path:
                    episode_output_path = output_path
                else:
                    episode_output_path = show_output_dir / f"{episode_name}_graph.json"

                # skip if output exists and not forcing.
                if episode_output_path.exists() and not force:
                    total_skipped += 1
                    progress.advance(task)
                    continue

                result = process_episode(
                    nlp,
                    episode_file,
                    show_name,
                    global_person_resolution=g_person_res,
                    global_place_resolution=g_place_res,
                    global_person_blocklist=g_person_block,
                    global_place_blocklist=g_place_block,
                )
                if result is None:
                    total_failed += 1
                    progress.advance(task)
                    continue

                graph_data, graph = result

                save_graph_data(graph_data, episode_output_path)
                save_adjacency_csv(graph, episode_output_path.parent / episode_output_path.stem)

                if visualize and graph.number_of_nodes() > 0:
                    # use custom output path for visualization if specified
                    if single_file_mode and output_path and episode_file == single_file_path:
                        viz_path = episode_output_path.with_suffix(".html")
                    else:
                        viz_path = show_output_dir / f"{episode_name}_graph.html"

                    visualize_graph(
                        graph,
                        viz_path,
                        title=humanize_title(episode_name),
                        subtitle=humanize_title(show_name),
                    )

                show_graphs.append(graph)
                show_persons.update(graph_data.persons)
                show_places.update(graph_data.places)

                total_processed += 1
                progress.advance(task)

        # generate per-show aggregated graph.
        if show_graphs:
            merged = merge_graphs(show_graphs)
            nodes, matrix = graph_to_adjacency_matrix(merged)

            edges = []
            for u, v, data in merged.edges(data=True):
                edge = {"source": u, "target": v, "weight": data.get("weight", 1)}
                if "relation" in data:
                    edge["relation"] = data["relation"]
                if "travelers" in data:
                    edge["travelers"] = data["travelers"]
                edges.append(edge)

            show_graph_data = ShowGraphData(
                show=show_name,
                episode_count=len(show_graphs),
                persons=sorted(show_persons),
                places=sorted(show_places),
                nodes=nodes,
                adjacency_matrix=matrix,
                edges=edges,
            )

            show_graph_path = summaries_dir / f"{show_name}_graph.json"
            save_graph_data(show_graph_data, show_graph_path)
            save_adjacency_csv(merged, summaries_dir / f"{show_name}_graph")

            if visualize and merged.number_of_nodes() > 0:
                visualize_graph(
                    merged,
                    summaries_dir / f"{show_name}_graph.html",
                    title=humanize_title(show_name),
                    subtitle=f"All episodes ({len(show_graphs)})",
                )

            logger.info(
                "show summary for %s: %d persons, %d places, %d edges",
                show_name,
                len(show_persons),
                len(show_places),
                merged.number_of_edges(),
            )

    # print summary table.
    console.print()
    table = Table(title="Entity Graph Generation Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green", justify="right")
    table.add_row("Shows processed", str(len(show_dirs)))
    table.add_row("Episodes found", str(total_episodes))
    table.add_row("Episodes processed", str(total_processed))
    table.add_row("Episodes skipped", str(total_skipped))
    table.add_row("Episodes failed", str(total_failed))
    console.print(table)

    console.print(f"\n[bold green]Output:[/bold green] {output_dir}")
    console.print(f"[bold green]Show summaries:[/bold green] {summaries_dir}")

    # regenerate index.json for the web app
    if total_processed > 0:
        console.print("\n[bold cyan]Updating web app index...[/bold cyan]")
        try:
            import subprocess
            index_script = script_dir / "generate_index.py"
            if index_script.exists():
                result = subprocess.run(
                    ["uv", "run", str(index_script)],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    console.print("[bold green]✓[/bold green] Web app index updated")
                else:
                    console.print(
                        f"[bold yellow]Warning: Failed to update index.json[/bold yellow]\n{result.stderr}"
                    )
        except Exception as e:
            console.print(f"[bold yellow]Warning: Could not update index.json: {e}[/bold yellow]")


if __name__ == "__main__":
    generate_entity_graphs()

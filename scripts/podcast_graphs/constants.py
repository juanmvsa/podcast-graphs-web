"""Constants, regex patterns, stopword sets, and lookup tables.

Centralizes all configuration values used across the pipeline so they
can be tuned in one place.
"""

from __future__ import annotations

import re

# ── spaCy NER label mapping ──────────────────────────────────────────────────

PLACE_LABELS: frozenset[str] = frozenset({"GPE", "LOC", "FAC"})

# ── Edge context limits ──────────────────────────────────────────────────────

MAX_CONTEXTS_PER_EDGE: int = 3
MAX_CONTEXTS_MERGED: int = 5
MAX_CONTEXTS_DISPLAY: int = 2

# ── Text truncation ─────────────────────────────────────────────────────────

MAX_SEGMENT_TEXT: int = 200
MAX_CONTEXT_DISPLAY_TEXT: int = 250

# ── Temporal thresholds (percentage of episode) ──────────────────────────────

EARLY_THRESHOLD: int = 33
LATE_THRESHOLD: int = 66

TEMPORAL_LABELS: dict[str, str] = {
    "early": "🕐 Early in episode",
    "middle": "🕑 Mid-episode",
    "late": "🕒 Late in episode",
}

# ── Sentiment emoji mapping ──────────────────────────────────────────────────

SENTIMENT_EMOJI: dict[str, str] = {
    "POSITIVE": "😊",
    "NEGATIVE": "😞",
    "NEUTRAL": "😐",
}

# ── Ambiguous geographic names ───────────────────────────────────────────────

AMBIGUOUS_GEO_NAMES: frozenset[str] = frozenset({
    "Jordan", "Israel", "Georgia", "Virginia", "Carolina", "Charlotte",
    "Dallas", "Houston", "Jackson", "Madison", "Austin", "Florence",
    "Hamilton", "Lincoln", "Nelson", "Washington", "Clinton", "Monroe",
    "Springfield",
})

# ── Speech fillers ───────────────────────────────────────────────────────────

SPEECH_FILLERS: frozenset[str] = frozenset({
    "um", "uh", "uh huh", "mm hmm", "hmm", "huh", "oh", "ah", "eh",
    "wow", "okay", "ok", "yeah", "yep", "yup", "nah", "nope",
    "right", "sure", "anyway", "anyways", "basically", "literally",
    "actually", "honestly", "obviously", "clearly", "totally",
    "definitely", "absolutely", "exactly", "really",
})

SPEECH_FILLER_PHRASES: list[str] = [
    "you know", "i mean", "kind of", "sort of", "i think",
    "i guess", "i feel like", "you know what i mean",
    "at the end of the day", "in terms of", "the thing is",
    "to be honest", "to be fair", "if you will",
]

# ── Entity validation thresholds ─────────────────────────────────────────────

MIN_ENTITY_LENGTH: int = 3
MIN_SINGLE_TOKEN_LENGTH: int = 5
MAX_ENTITY_TOKENS: int = 4

# ── Regex patterns for entity normalization ──────────────────────────────────

REPEATED_PATTERN: re.Pattern[str] = re.compile(r"^(.{1,4})\1{2,}")
POSSESSIVE_SUFFIX: re.Pattern[str] = re.compile(r"['\u2019]s$", re.IGNORECASE)
LEADING_ARTICLE: re.Pattern[str] = re.compile(r"^(?:the|a|an)\s+", re.IGNORECASE)
LEADING_PROFANITY: re.Pattern[str] = re.compile(
    r"^(?:fuck(?:ing)?|shit(?:ty)?|damn(?:ed)?|bloody|freaking)\s+", re.IGNORECASE
)
LEADING_NOISE: re.Pattern[str] = re.compile(
    r"^(?:pro-?|anti-?|not|all|no|find|this|her|his|versus|vs\.?|googling|like|just)\s+",
    re.IGNORECASE,
)
NON_ALPHA: re.Pattern[str] = re.compile(r"[^a-zA-Z]")
CONTAINS_DIGIT: re.Pattern[str] = re.compile(r"\d")
ABBREVIATION_DOTS: re.Pattern[str] = re.compile(
    r"(?<!\w)([A-Za-z])\.(?=[A-Za-z]\.|\s|$)"
)
TRAILING_JUNK: re.Pattern[str] = re.compile(r"[,;:!?\.\s]+$")

# ── Person stopwords (common misclassifications) ────────────────────────────

PERSON_STOPWORDS: frozenset[str] = frozenset({
    # filler words and interjections
    "yay", "ooh", "rah", "hey", "wow", "yo", "huh", "ugh", "hmm",
    "mm-hmm", "uh-huh", "uh-oh", "oops", "intro", "outro",
    # familial / generic references
    "mom", "dad", "god", "babe", "dude", "bro", "sis", "hon", "sir",
    "bruh", "bestie", "hun", "sweetie", "buddy", "girl", "baby",
    "madam", "mister", "missus", "kiddo", "hubby", "wifey",
    # common nouns / adjectives misclassified
    "idol", "main", "push", "drag", "crow", "garb", "toad", "hiss",
    "huns", "turd", "hurd", "tick", "tons", "knee", "miss", "watt",
    "dole", "euro", "yada", "pun", "trad", "law", "mav", "shall",
    "pride", "beast", "krabs", "verdict", "emoji", "jubilee", "athlet",
    "athleta", "gener", "lesbian", "lesbians", "zionist", "zionists",
    "trans", "chick",
    # diseases / medical terms
    "covid", "monkeypox", "mpox", "aids", "adhd",
    # zodiac signs
    "cancer", "aries", "libra", "gemini", "virgo", "scorpio", "pisces",
    "taurus", "capricorn", "sagittarius", "aquarius", "leo",
    # generation labels
    "gen z", "gen x", "gen alpha", "boomer", "millennial",
    # religious / cultural terms
    "shabbat", "ramadan", "christmas", "easter", "kwanzaa", "judaism",
    "satan", "allah",
    # slang / internet culture
    "hawk tua", "stan twitter", "pop crave", "darvo", "lgbtq", "lgbtq+", "lgbt",
    # fictional / brand
    "barbie", "minnie mouse", "minnie",
    # role labels / generic terms
    "youtuber", "tiktoker", "influencer", "podcaster", "wikipedia", "rfk jr",
})

# ── Organizations / brands misclassified as PERSON ──────────────────────────

ORG_AS_PERSON: frozenset[str] = frozenset({
    # social media / tech platforms
    "twitter", "instagram", "meta", "facebook", "google", "apple",
    "microsoft", "amazon", "netflix", "spotify", "reddit", "snapchat",
    "pinterest", "linkedin", "whatsapp", "telegram", "signal", "discord",
    "slack", "zoom", "teams", "skype", "tiktok", "youtube", "fox", "cnn",
    "msnbc", "nbc", "abc", "cbs", "hbo", "hulu", "disney", "openai",
    "spacex", "tesla", "uber", "lyft", "airbnb", "paypal", "venmo",
    "shopify", "twitch", "tumblr", "myspace", "grindr", "blue sky",
    "bluesky", "truth social", "threads",
    # brands / products / companies
    "blueland", "bud light", "bud lights", "protein plus", "all bud light",
    "no bud light", "ticketmaster", "coachella", "stonewall", "oscar mayer",
    "hallmark", "shein", "postmates",
    # media / organizations / shows
    "turning point", "daily wire", "babylon bee", "drag race", "fox news",
    "breitbart", "infowars", "morning joe", "dance moms", "maintenance phase",
    "rehash podcast", "politico", "teen vogue", "bustle", "wired", "insta",
})

# ── Place abbreviation expansions ────────────────────────────────────────────

PLACE_ABBREVIATIONS: dict[str, str] = {
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

# ── Place stopwords ──────────────────────────────────────────────────────────

PLACE_STOPWORDS: frozenset[str] = frozenset({
    "ai", "anyway", "apologia", "backlash", "beatlemania", "berserk",
    "biphobia", "blackface", "blackout", "blogging", "bottoms", "burning",
    "candyland", "caucasian", "chemophobia", "cisphobia", "dearest",
    "dysphoria", "euphoria", "fandom", "hashtag", "hell", "hello",
    "hemophilia", "homeland", "hysteria", "imagine", "insane", "intro",
    "laboratory", "mpox", "naked", "phobia", "propaganda", "provax",
    "psycho", "puritan", "quiet", "scientology", "transphobia", "totally",
    "wonderland", "beholden",
    # short garbage / non-place tokens
    "jew", "bud", "gay", "pov", "dah", "hrt", "nra", "q&a",
    "jan", "san", "ark", "zim", "f.a", "j.k",
    # zodiac / concepts
    "aries", "cancer", "libra", "gemini", "virgo",
    # demonyms and group labels
    "gazan", "swifties", "trans athletes",
    # organizations / platforms misclassified as places
    "reddit", "netflix", "spotify", "grindr", "youtube", "myspace",
    "blue sky", "bluesky", "daily wire", "drag race", "ticketmaster",
    "teen vogue", "bustle", "wired", "blueland", "shopify", "truth social",
    "threads", "spacex", "openai", "pinterest", "hinge", "babylon bee",
    # generic / vague terms
    "vantage", "overton", "pride", "homo sapiens", "ozempic", "satan",
    "kool-aid", "speedo",
    # person names misclassified as places
    "paris hilton", "kid rock", "rock hudson", "cam dallas",
    "asia jackson", "zendaya",
    # brand/product/show names misclassified as places
    "protein plus", "bud light", "coachella", "comedy central",
    "craigslist", "met gala", "party city", "louis vuitton", "alibaba",
    "postmates", "tumblr", "oasis", "zynga", "young turks", "skyhorse",
    # compound garbage
    "point usa", "ac la", "gen alpha", "anti-israel", "pro-israel",
    "anti-black", "anti-lgbt", "new black", "new photo", "red states",
    "jubilee overton", "trading spaces", "dream tour", "velvet glove cast",
    "kamala hq", "america fest", "broadway deschanel", "yellow king",
    "moon lander", "highways", "easter", "juneteenth", "purim",
    "intifada", "wi-fi", "tic tacs",
})

# ── Known place merges ───────────────────────────────────────────────────────

KNOWN_PLACE_MERGES: dict[str, str] = {
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

# ── Visualization colors ─────────────────────────────────────────────────────

PERSON_COLOR: str = "#4FC3F7"
PLACE_COLOR: str = "#FF8A65"
MOVEMENT_EDGE_COLOR: str = "#AB47BC"
ASSOCIATION_EDGE_COLOR: str = "#90A4AE"
SENTIMENT_POSITIVE_COLOR: str = "#66BB6A"
SENTIMENT_NEGATIVE_COLOR: str = "#EF5350"
SENTIMENT_NEUTRAL_COLOR: str = "#90A4AE"

# ── Title formatting ─────────────────────────────────────────────────────────

TITLE_MINOR_WORDS: frozenset[str] = frozenset({
    "a", "an", "and", "as", "at", "but", "by", "for", "if", "in", "nor",
    "of", "on", "or", "so", "the", "to", "up", "vs", "yet", "with",
})

# ── Wikipedia disambiguation ─────────────────────────────────────────────────

WIKIPEDIA_USER_AGENT: str = "podcast-graphs-web/0.2.0 (entity-disambiguation)"

WIKIPEDIA_PERSON_INDICATORS: list[str] = [
    "born", "is a", "was a", "politician", "actor", "actress",
    "singer", "author", "journalist", "presenter", "host",
    "comedian", "writer", "activist", "entrepreneur", "athlete",
    "player", "coach", "director", "producer", "musician",
    "rapper", "model", "influencer", "youtuber", "podcast",
]

# ── NLP batch processing ─────────────────────────────────────────────────────

NLP_PIPE_BATCH_SIZE: int = 256

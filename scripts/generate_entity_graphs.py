#!/usr/bin/env python3
"""
Named entity recognition and relationship graph generation for podcast transcripts.

This is a thin wrapper that delegates to the podcast_graphs package.
See podcast_graphs/ for the implementation.

Usage:
    uv run scripts/generate_entity_graphs.py
    uv run scripts/generate_entity_graphs.py --input path/to/transcript.json
    uv run scripts/generate_entity_graphs.py --input-dir path/to/parent/directory
    uv run scripts/generate_entity_graphs.py --force --visualize
"""

from __future__ import annotations

import sys
from pathlib import Path

# add scripts to path for utils and podcast_graphs imports
script_dir = Path(__file__).resolve().parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from podcast_graphs.cli import generate_entity_graphs

if __name__ == "__main__":
    generate_entity_graphs()

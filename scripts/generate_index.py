#!/usr/bin/env python3
"""
Generate index.json for the podcast graphs web app.

Scans the graphs/ directory and creates a JSON index of all available
HTML graph files organized by show.
"""

from __future__ import annotations

import json
from pathlib import Path


def humanize_filename(filename: str) -> str:
    """Convert a snake_case filename to a human-readable title."""
    # Remove _graph suffix and .html extension
    name = filename.replace("_graph.html", "").replace("_graph", "")

    # Replace underscores with spaces
    name = name.replace("_", " ")

    # Capitalize each word, but handle special cases
    words = name.split()
    result = []

    # Minor words that should be lowercase (unless first/last)
    minor_words = {
        "a", "an", "and", "as", "at", "but", "by", "for", "if", "in", "nor",
        "of", "on", "or", "so", "the", "to", "up", "vs", "yet", "with"
    }

    for i, word in enumerate(words):
        # Always capitalize first and last words
        if i == 0 or i == len(words) - 1:
            result.append(word.capitalize())
        # Keep minor words lowercase
        elif word.lower() in minor_words:
            result.append(word.lower())
        else:
            result.append(word.capitalize())

    return " ".join(result)


def scan_graphs_directory(graphs_dir: Path) -> dict:
    """Scan the graphs directory and build an index structure."""
    if not graphs_dir.exists():
        return {"shows": [], "lastUpdated": ""}

    shows = []

    # Look for show directories (skip 'summaries')
    for show_dir in sorted(graphs_dir.iterdir()):
        if not show_dir.is_dir() or show_dir.name == "summaries" or show_dir.name.startswith("."):
            continue

        show_name = show_dir.name
        episodes = []

        # Collect episodes from HTML graph files
        html_episodes = set()
        for html_file in sorted(show_dir.glob("*_graph.html")):
            # Skip normalized variants if non-normalized version exists
            if "_normalized_graph.html" in html_file.name:
                base_name = html_file.name.replace("_normalized_graph.html", "_graph.html")
                if (show_dir / base_name).exists():
                    continue

            episode_title = humanize_filename(html_file.stem)
            relative_path = f"graphs/{show_name}/{html_file.name}"
            html_episodes.add(html_file.stem.replace("_graph", ""))

            episodes.append({
                "title": episode_title,
                "path": relative_path,
                "filename": html_file.name
            })

        # Also discover episodes from JSON graph files that lack HTML
        for json_file in sorted(show_dir.glob("*_graph.json")):
            episode_stem = json_file.stem.replace("_graph", "")
            if episode_stem in html_episodes:
                continue  # already indexed via HTML

            # Skip normalized variants
            if "_normalized_graph" in json_file.name:
                base_name = json_file.name.replace("_normalized_graph.json", "_graph.json")
                if (show_dir / base_name).exists():
                    continue

            episode_title = humanize_filename(json_file.stem)
            # Link to HTML if it exists, otherwise link to JSON
            html_path = json_file.with_suffix(".html")
            if html_path.exists():
                relative_path = f"graphs/{show_name}/{html_path.name}"
            else:
                relative_path = f"graphs/{show_name}/{json_file.name}"

            episodes.append({
                "title": episode_title,
                "path": relative_path,
                "filename": json_file.name
            })

        if episodes:
            # Check for legacy summary file (all episodes)
            summary_file = graphs_dir / "summaries" / f"{show_name}_graph.html"
            summary_path = None
            if summary_file.exists():
                summary_path = f"graphs/summaries/{summary_file.name}"

            # Check for per-topic summaries (HTML or JSON)
            topic_summaries = []
            show_summaries_dir = graphs_dir / "summaries" / show_name
            if show_summaries_dir.exists() and show_summaries_dir.is_dir():
                seen_topics = set()
                for topic_file in sorted(show_summaries_dir.glob("*_graph.html")):
                    topic_title = humanize_filename(topic_file.stem)
                    topic_path = f"graphs/summaries/{show_name}/{topic_file.name}"
                    seen_topics.add(topic_file.stem.replace("_graph", ""))
                    topic_summaries.append({
                        "title": topic_title,
                        "path": topic_path,
                        "filename": topic_file.name
                    })
                # Also include JSON-only topic summaries
                for topic_file in sorted(show_summaries_dir.glob("*_graph.json")):
                    topic_stem = topic_file.stem.replace("_graph", "")
                    if topic_stem in seen_topics:
                        continue
                    topic_title = humanize_filename(topic_file.stem)
                    topic_path = f"graphs/summaries/{show_name}/{topic_file.name}"
                    topic_summaries.append({
                        "title": topic_title,
                        "path": topic_path,
                        "filename": topic_file.name
                    })

            shows.append({
                "name": show_name,
                "displayName": humanize_filename(show_name),
                "episodeCount": len(episodes),
                "episodes": episodes,
                "summaryPath": summary_path,
                "topicSummaries": topic_summaries
            })

    from datetime import datetime
    return {
        "shows": shows,
        "lastUpdated": datetime.now().isoformat(),
        "totalShows": len(shows),
        "totalEpisodes": sum(show["episodeCount"] for show in shows)
    }


def main():
    """Generate the index.json file."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate index.json for the podcast graphs web app.")
    parser.add_argument("--graphs-dir", type=Path, default=None,
                        help="Path to graphs directory (default: <project-root>/graphs)")
    parser.add_argument("--output", type=Path, default=None,
                        help="Output path for index.json (default: <project-root>/index.json)")
    args = parser.parse_args()

    # Determine paths
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    graphs_dir = args.graphs_dir or (project_root / "graphs")
    output_file = args.output or (project_root / "index.json")

    print(f"Scanning graphs directory: {graphs_dir}")

    # Generate index
    index_data = scan_graphs_directory(graphs_dir)

    # Write to file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)

    print(f"✓ Generated index.json with {index_data['totalShows']} shows and {index_data['totalEpisodes']} episodes")
    print(f"  Output: {output_file}")

    # Print summary
    for show in index_data["shows"]:
        topic_count = len(show.get("topicSummaries", []))
        summary_info = ""
        if show.get("summaryPath"):
            summary_info += " [legacy summary]"
        if topic_count > 0:
            summary_info += f" [{topic_count} topic summaries]"
        print(f"  - {show['displayName']}: {show['episodeCount']} episodes{summary_info}")


if __name__ == "__main__":
    main()

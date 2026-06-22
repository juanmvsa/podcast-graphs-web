"""CLI entry points for the podcast graphs pipeline.

Provides click-based command-line interface for entity graph generation.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path

import click
import networkx as nx
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from podcast_graphs.graph.construction import merge_graphs
from podcast_graphs.graph.serialization import (
    graph_to_adjacency_matrix,
    save_adjacency_csv,
    save_graph_data,
    serialize_edges,
)
from podcast_graphs.graph.visualization import humanize_title, visualize_graph
from podcast_graphs.pipeline import (
    apply_topic_curations,
    build_global_resolution_maps,
    collect_raw_entities,
    generate_per_topic_summaries,
    process_episode,
)
from podcast_graphs.topics import cluster_episode_topics, prepare_topic_document
from podcast_graphs.types import ShowGraphData

logger = logging.getLogger(__name__)

# resolve project paths
_SCRIPT_DIR = Path(__file__).resolve().parent.parent  # scripts/
_PROJECT_ROOT = _SCRIPT_DIR.parent


@click.command()
@click.option(
    "--input", "-i", "input_path",
    type=click.Path(path_type=Path),
    help="Input file or directory with transcripts (overrides --transcripts-dir).",
)
@click.option(
    "--input-dir", "-d", "input_dir_path",
    type=click.Path(path_type=Path),
    help="Recursively process all subdirectories as shows.",
)
@click.option(
    "--output", "-o", "output_path",
    type=click.Path(path_type=Path),
    help="Output file path (for single file processing).",
)
@click.option(
    "--transcripts-dir",
    type=click.Path(path_type=Path),
    default=Path("transcripts_with_speaker_labels_postprocessed_with_utterance_and_document_labels"),
    help="Directory with speaker-labeled transcripts.",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path("graphs"),
    help="Output directory for graph files.",
)
@click.option(
    "--shows", multiple=True,
    help="Process only specific shows (can be repeated).",
)
@click.option(
    "--spacy-model", type=str, default="en_core_web_lg",
    help="spaCy model for NER.",
)
@click.option("--force", is_flag=True, help="Force reprocessing of all files.")
@click.option("--visualize", is_flag=True, help="Generate interactive HTML visualizations.")
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Logging level.",
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
    """Extract PERSON/PLACE entities and generate relationship graphs."""
    # lazy imports for startup speed
    import spacy

    from utils.rich_utils import console, setup_logging

    setup_logging(log_level)

    single_file_mode = False
    single_file_path: Path | None = None
    recursive_mode = False

    # handle input-dir flag
    if input_dir_path:
        input_dir_path = input_dir_path.resolve()
        if not input_dir_path.exists():
            console.print(f"[bold red]Error: input directory not found: {input_dir_path}[/bold red]")
            sys.exit(1)
        if not input_dir_path.is_dir():
            console.print(f"[bold red]Error: --input-dir must be a directory: {input_dir_path}[/bold red]")
            sys.exit(1)
        transcripts_dir = input_dir_path
        recursive_mode = True
        console.print(f"[dim]Recursive mode: scanning {input_dir_path} for subdirectories[/dim]")
    elif input_path:
        input_path = input_path.resolve()
        if not input_path.exists():
            console.print(f"[bold red]Error: input path not found: {input_path}[/bold red]")
            sys.exit(1)
        if input_path.is_file():
            single_file_mode = True
            single_file_path = input_path
            # grandparent so show_dir scanning finds the parent as a show
            transcripts_dir = input_path.parent.parent
            shows = (input_path.parent.name,)
        else:
            transcripts_dir = input_path

    if output_path:
        output_path = output_path.resolve()
        if not single_file_mode:
            console.print(
                "[bold yellow]Warning: --output flag is only used with single file input. "
                "Using --output-dir for directory processing.[/bold yellow]"
            )
        else:
            output_dir = output_path.parent

    transcripts_dir = transcripts_dir.resolve()
    output_dir = output_dir.resolve()

    if not transcripts_dir.exists():
        console.print(f"[bold red]Error: transcripts directory not found: {transcripts_dir}[/bold red]")
        sys.exit(1)

    # load spacy model
    console.print(f"[bold cyan]Loading spaCy model:[/bold cyan] {spacy_model}")
    try:
        nlp = spacy.load(spacy_model, disable=["parser", "lemmatizer"])
    except OSError:
        console.print(
            f"[bold red]Error: spaCy model '{spacy_model}' not found. "
            f"Install it with: uv run python -m spacy download {spacy_model}[/bold red]"
        )
        sys.exit(1)

    # collect show directories
    if recursive_mode:
        show_dirs: list[Path] = []
        for root, dirs, files in transcripts_dir.walk():
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            if any(f.endswith(".json") for f in files):
                show_dirs.append(Path(root))
        show_dirs = sorted(show_dirs)
        console.print(f"[dim]Found {len(show_dirs)} directories with JSON files[/dim]")
    else:
        show_dirs = sorted(
            d for d in transcripts_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
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

    episodes_for_clustering: list[dict[str, str]] = []
    all_episode_graphs: dict[str, dict[str, object]] = {}

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

        # pass 1: collect entities for global normalization
        console.print("  [dim]Pass 1: collecting entities for global normalization...[/dim]")
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
            BarColumn(), MofNCompleteColumn(), TimeElapsedColumn(), console=console,
        ) as progress:
            task = progress.add_task(f"  scan {show_name}", total=len(episode_files))
            show_raw_persons, show_raw_places = collect_raw_entities(
                nlp, episode_files, progress, task
            )

        # build global resolution maps
        maps = build_global_resolution_maps(show_raw_persons, show_raw_places)
        if maps.person_resolution:
            console.print(f"  [dim]Global person resolutions: {len(maps.person_resolution)}[/dim]")
        if maps.place_resolution:
            console.print(f"  [dim]Global place resolutions: {len(maps.place_resolution)}[/dim]")

        # pass 2: process episodes with global normalization
        console.print("  [dim]Pass 2: generating graphs with normalized entities...[/dim]")
        show_graphs: list[nx.DiGraph] = []
        show_persons: set[str] = set()
        show_places: set[str] = set()

        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
            BarColumn(), MofNCompleteColumn(), TimeElapsedColumn(), console=console,
        ) as progress:
            task = progress.add_task(f"  {show_name}", total=len(episode_files))

            for episode_file in episode_files:
                total_episodes += 1
                episode_name = episode_file.stem

                if single_file_mode and output_path and episode_file == single_file_path:
                    episode_output_path = output_path
                else:
                    episode_output_path = show_output_dir / f"{episode_name}_graph.json"

                if episode_output_path.exists() and not force:
                    total_skipped += 1
                    progress.advance(task)
                    continue

                result = process_episode(
                    nlp, episode_file, show_name,
                    global_person_resolution=maps.person_resolution,
                    global_place_resolution=maps.place_resolution,
                    global_person_blocklist=maps.person_blocklist,
                    global_place_blocklist=maps.place_blocklist,
                )
                if result is None:
                    total_failed += 1
                    progress.advance(task)
                    continue

                graph_data, graph = result
                save_graph_data(graph_data, episode_output_path)
                save_adjacency_csv(graph, episode_output_path.parent / episode_output_path.stem)

                if visualize and graph.number_of_nodes() > 0:
                    if single_file_mode and output_path and episode_file == single_file_path:
                        viz_path = episode_output_path.with_suffix(".html")
                    else:
                        viz_path = show_output_dir / f"{episode_name}_graph.html"
                    visualize_graph(
                        graph, viz_path,
                        title=humanize_title(episode_name),
                        subtitle=humanize_title(show_name),
                    )

                show_graphs.append(graph)
                show_persons.update(graph_data.persons)
                show_places.update(graph_data.places)

                # key by show/episode so identically named episodes in different
                # shows do not overwrite each other.
                episode_key = f"{show_name}/{episode_name}"
                all_episode_graphs[episode_key] = {"graph": graph, "show": show_name}

                # collect text for topic clustering
                try:
                    with episode_file.open() as f:
                        ep_data = json.load(f)
                        segments = ep_data.get("segments", [])
                        episode_text = prepare_topic_document(segments)
                        if episode_text.strip():
                            episodes_for_clustering.append({
                                "name": episode_key,
                                "show": show_name,
                                "text": episode_text,
                                "file": str(episode_file),
                            })
                except Exception as e:
                    logger.warning("Could not collect text for %s: %s", episode_name, e)

                total_processed += 1
                progress.advance(task)

        # generate per-show aggregated graph
        if show_graphs:
            merged = merge_graphs(show_graphs)
            nodes, matrix = graph_to_adjacency_matrix(merged)
            edges = serialize_edges(merged)

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
                show_name, len(show_persons), len(show_places), merged.number_of_edges(),
            )

    # topic clustering
    if episodes_for_clustering and len(episodes_for_clustering) >= 3:
        console.print("\n[bold cyan]Clustering episodes by topics...[/bold cyan]")
        try:
            topic_results = cluster_episode_topics(
                episodes_for_clustering, min_topic_size=2, nr_topics=None
            )

            topics_output_path = output_dir / "topics.json"
            labels_path = output_dir / "topic_labels.json"

            if labels_path.exists():
                apply_topic_curations(topic_results, labels_path)

            with topics_output_path.open("w") as f:
                json.dump(topic_results, f, indent=2)

            num_topics = len(topic_results.get("topics", []))
            num_clustered = len(topic_results.get("episode_topics", {}))
            metrics = topic_results.get("metrics", {})
            console.print(
                f"[bold green]\u2713[/bold green] Identified {num_topics} topics "
                f"across {num_clustered} episodes"
            )
            if metrics:
                console.print(
                    f"[dim]  diversity={metrics.get('topic_diversity', 0):.2f}  "
                    f"outliers={metrics.get('num_outlier_episodes', 0)}[/dim]"
                )
            console.print(f"[dim]Topics saved to: {topics_output_path}[/dim]")

            if all_episode_graphs and visualize:
                try:
                    generate_per_topic_summaries(
                        topic_results=topic_results,
                        all_episode_graphs=all_episode_graphs,
                        output_dir=output_dir,
                        visualize=True,
                        topics_per_graph=3,
                    )
                except Exception as e:
                    console.print(f"[bold yellow]Warning: Per-topic summary generation failed: {e}[/bold yellow]")
                    logger.exception("Per-topic summary error")

        except Exception as e:
            console.print(f"[bold yellow]Warning: Topic clustering failed: {e}[/bold yellow]")
            logger.exception("Topic clustering error")

    # print summary table
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

    # regenerate index.json
    if total_processed > 0:
        console.print("\n[bold cyan]Updating web app index...[/bold cyan]")
        try:
            index_script = _SCRIPT_DIR / "generate_index.py"
            if index_script.exists():
                result = subprocess.run(
                    ["uv", "run", str(index_script)],
                    cwd=_PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    console.print("[bold green]\u2713[/bold green] Web app index updated")
                else:
                    console.print(
                        f"[bold yellow]Warning: Failed to update index.json[/bold yellow]\n{result.stderr}"
                    )
        except Exception as e:
            console.print(f"[bold yellow]Warning: Could not update index.json: {e}[/bold yellow]")

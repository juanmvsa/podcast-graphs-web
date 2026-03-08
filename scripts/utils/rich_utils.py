"""Rich console and logging utilities."""

import logging
from rich.console import Console
from rich.logging import RichHandler

# create a shared console instance
console = Console()


def setup_logging(level: str = "INFO") -> None:
    """configure logging with rich output."""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )

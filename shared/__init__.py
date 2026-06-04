"""Shared utilities for county data pipelines."""

import os
import logging
from pathlib import Path

logger = logging.getLogger("county-data")


def ensure_dir(path: Path) -> Path:
    """Create directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging for the pipeline."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def data_dir(state: str = "fl") -> Path:
    """Get the data directory for a state."""
    base = Path(os.environ.get("COUNTY_DATA_DIR", Path.home() / "county-data"))
    return ensure_dir(base / state / "data")

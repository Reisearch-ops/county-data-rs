#!/usr/bin/env python3
"""Run the full Florida pipeline: download NAL+SDF for all 67 counties."""

from fl.downloader import download_all, main as downloader_main
from shared import setup_logging

if __name__ == "__main__":
    # When run directly, delegate to downloader main
    downloader_main()

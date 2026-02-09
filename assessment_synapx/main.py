#!/usr/bin/env python3
"""Top-level entrypoint — lightweight wrapper that imports the fnol_agent package."""
import sys

from fnol_agent.cli import main


if __name__ == "__main__":
    main(sys.argv)

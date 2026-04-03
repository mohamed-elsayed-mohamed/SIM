"""Shared repository paths and the pipeline logger."""

from __future__ import annotations

import logging
from pathlib import Path

# Repository root (SIM): parent of Build/
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("build")

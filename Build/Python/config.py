"""Load and merge `build_config.json` with CLI arguments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .constants import REPO_ROOT, log


def load_config(args: argparse.Namespace) -> dict:
    """Merge build_config.json with CLI overrides. CLI wins."""
    config_path = REPO_ROOT / "build_config.json"
    cfg: dict = {}
    if config_path.exists():
        with config_path.open() as f:
            cfg = json.load(f)
        log.info("[config] Loaded %s", config_path)
    else:
        log.warning("[config] build_config.json not found — using defaults")

    # CLI overrides
    if args.config:
        cfg["config"] = args.config
    if args.platform:
        cfg["platform"] = args.platform
    if args.artifact_repo:
        cfg["artifact_repo"] = args.artifact_repo
    if args.version:
        cfg["version"] = args.version

    # Defaults
    cfg.setdefault("config", "Release")
    cfg.setdefault("platform", "x64")
    cfg.setdefault("artifact_repo", str(REPO_ROOT / "artifacts"))
    cfg.setdefault("version", "0.0.0")

    log.info(
        "[config] config=%s  platform=%s  version=%s  artifact_repo=%s",
        cfg["config"], cfg["platform"], cfg["version"], cfg["artifact_repo"],
    )
    return cfg

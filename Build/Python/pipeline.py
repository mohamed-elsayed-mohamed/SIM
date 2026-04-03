"""CLI argument parsing and orchestration of all pipeline stages."""

from __future__ import annotations

import argparse
import sys

from .compile_stage import stage_compile
from .config import load_config
from .constants import log
from .pack_stage import stage_pack
from .publish_stage import stage_publish
from .resolve_deps import stage_resolve_deps
from .tool_detection import detect_tools
from .vcpkg_helpers import write_vcpkg_overlay_triplet_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="DevOps Case Study — multi-language build pipeline"
    )
    parser.add_argument("--config",        default="", help="Build configuration (Release|Debug)")
    parser.add_argument("--version",       default="", help="Artifact version (semver, e.g. 1.0.0)")
    parser.add_argument("--platform",      default="", help="Target platform (x64)")
    parser.add_argument("--artifact-repo", default="", help="Artifact output folder")
    parser.add_argument(
        "--write-overlay-triplet",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def main() -> None:
    if sys.version_info < (3, 9):
        print("ERROR: Python 3.9+ is required.", file=sys.stderr)
        sys.exit(1)

    args = parse_args()

    if args.write_overlay_triplet:
        if sys.platform != "win32":
            log.error("--write-overlay-triplet is only supported on Windows.")
            sys.exit(1)
        p = write_vcpkg_overlay_triplet_dir()
        if p is None:
            log.error("Failed to write overlay triplet (Windows SDK not found).")
            sys.exit(1)
        log.info("Wrote overlay triplet directory: %s", p)
        sys.exit(0)

    cfg = load_config(args)
    tools = detect_tools(cfg)

    stage_resolve_deps(tools, cfg)
    stage_compile(tools, cfg)
    stage_pack(tools, cfg)
    stage_publish(tools, cfg)

    log.info("Build pipeline completed successfully. Version: %s", cfg["version"])

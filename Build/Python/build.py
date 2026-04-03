#!/usr/bin/env python3
"""
Entry point for the DevOps Case Study build pipeline.

Usage::

    python Build/Python/build.py --config Release --version 1.0.0
    python Build/Python/build.py --config Debug   --version 1.0.0 --platform x64

Implementation is split under ``Build/Python/`` (see ``Build/Python/README.md``).
The stages run in order: tool detection -> config -> resolve dependencies -> compile -> pack -> publish.

Pipeline stages (delegated to ``Build.Python.pipeline``):

1. **detect_tools** -- Fail fast if MSBuild, vcpkg, dotnet, etc. are missing; optional Unity.
2. **load_config** -- Merge ``build_config.json`` with CLI overrides.
3. **resolve_deps** -- vcpkg install (ProjectA, ProjectB), dotnet restore (ProjectC, ProjectD).
4. **compile** -- MSBuild A->B, dotnet build C->D, optional Unity CLI build for ProjectE.
5. **pack** -- ``dotnet pack`` SIM.ProjectC and SIM.ProjectD with ``--version`` as ``PackageVersion``.
6. **publish** -- Copy versioned artifacts (including ``.nupkg``) to ``<artifact_repo>/Python/<version>_<timestamp>/``.
"""

from __future__ import annotations

import pathlib
import sys

# Ensure repo root is on sys.path so "Build.Python" package resolves
_repo = str(pathlib.Path(__file__).resolve().parents[2])
if _repo not in sys.path:
    sys.path.insert(0, _repo)

from Build.Python.pipeline import main  # noqa: E402


if __name__ == "__main__":
    main()

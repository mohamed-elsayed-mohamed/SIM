"""Stage: dotnet pack for SIM.ProjectC and SIM.ProjectD (matches CI)."""

from __future__ import annotations

from pathlib import Path

from .constants import REPO_ROOT, log
from .process import run


def stage_pack(tools: dict, cfg: dict) -> None:
    """Create versioned .nupkg files; requires a successful compile (uses ``--no-build``)."""
    dotnet: Path = tools["dotnet"]
    build_config: str = cfg["config"]
    version: str = cfg["version"]

    log.info("[pack] Packing NuGet packages (PackageVersion=%s)...", version)

    run(
        [
            str(dotnet),
            "pack",
            str(REPO_ROOT / "ProjectC" / "ProjectC.csproj"),
            "-c",
            build_config,
            "--no-build",
            "-p",
            f"PackageVersion={version}",
        ],
        stage="pack",
    )
    run(
        [
            str(dotnet),
            "pack",
            str(REPO_ROOT / "ProjectD" / "ProjectD.csproj"),
            "-c",
            build_config,
            "--no-build",
            "-p",
            f"PackageVersion={version}",
        ],
        stage="pack",
    )

    log.info("[pack] NuGet packages created successfully.")


def find_packed_nupkg(
    project_subdir: str, package_id: str, build_config: str, version: str
) -> Path | None:
    """Return ``{PackageId}.{PackageVersion}.nupkg`` under ``bin/<config>/`` (avoids stale packages)."""
    root = REPO_ROOT / project_subdir / "bin" / build_config
    if not root.is_dir():
        return None
    exact = root / f"{package_id}.{version}.nupkg"
    if exact.exists():
        return exact
    # Fallback: SDK occasionally nests output (prefer exact version in filename)
    matches = [p for p in root.rglob(f"{package_id}.{version}.nupkg") if p.is_file()]
    return matches[-1] if matches else None

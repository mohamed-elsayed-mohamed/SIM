"""Stage: copy versioned binaries to the artifact folder and write manifest.json."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from .constants import REPO_ROOT, log
from .pack_stage import find_packed_nupkg


def stage_publish(tools: dict, cfg: dict) -> None:  # noqa: ARG001
    version: str = cfg["version"]
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    artifact_base = Path(cfg["artifact_repo"]).resolve()
    out_dir = artifact_base / "Python" / f"{version}_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    log.info("[publish] Publishing version %s → %s", version, out_dir)

    build_config = cfg["config"]
    platform = cfg["platform"]

    artifacts: list[tuple[Path, str]] = [
        # C++ DLLs
        (
            REPO_ROOT / "ProjectA" / platform / build_config / "ProjectA.dll",
            "ProjectA.dll",
        ),
        (
            REPO_ROOT / "ProjectB" / platform / build_config / "ProjectB.dll",
            "ProjectB.dll",
        ),
        # C# DLLs (net8.0)
        (
            REPO_ROOT / "ProjectC" / "bin" / build_config / "net8.0" / "ProjectC.dll",
            "ProjectC.dll",
        ),
        (
            REPO_ROOT / "ProjectD" / "bin" / build_config / "net8.0" / "ProjectD.dll",
            "ProjectD_net8.dll",
        ),
        # C# DLLs (netstandard2.1) — for Unity consumption
        (
            REPO_ROOT / "ProjectD" / "bin" / build_config / "netstandard2.1" / "ProjectD.dll",
            "ProjectD_netstandard2.1.dll",
        ),
    ]

    missing = []
    for src, name in artifacts:
        if src.exists():
            shutil.copy2(src, out_dir / name)
            log.info("[publish] Copied %s", name)
        else:
            log.warning("[publish] Not found (skipping): %s", src)
            missing.append(str(src))

    # Unity build output (optional) — copy the entire player folder
    unity_build_dir = REPO_ROOT / "ProjectE" / "Builds" / "StandaloneWindows64"
    unity_exe = unity_build_dir / "ProjectE.exe"
    if unity_exe.exists():
        unity_dest = out_dir / "ProjectE-StandaloneWindows64"
        shutil.copytree(unity_build_dir, unity_dest)
        log.info("[publish] Copied Unity build folder → %s", unity_dest)
    else:
        log.warning("[publish] Unity build not found (skipping): %s", unity_exe)
        missing.append(str(unity_exe))

    # NuGet packages from pack stage
    nupkg_specs = [("ProjectC", "SIM.ProjectC"), ("ProjectD", "SIM.ProjectD")]
    nupkg_names: list[str] = []
    for proj_dir, pkg_id in nupkg_specs:
        src = find_packed_nupkg(proj_dir, pkg_id, build_config, version)
        if src and src.exists():
            dest_name = src.name
            shutil.copy2(src, out_dir / dest_name)
            log.info("[publish] Copied %s", dest_name)
            nupkg_names.append(dest_name)
        else:
            log.warning("[publish] NuGet package not found (skipping): %s", pkg_id)
            missing.append(str(src or f"{pkg_id}*.nupkg"))

    # Write a version manifest
    all_artifact_names = [name for _, name in artifacts] + nupkg_names
    if unity_exe.exists():
        all_artifact_names.append("ProjectE-StandaloneWindows64/")
    manifest = {
        "version": version,
        "config": build_config,
        "platform": platform,
        "artifacts": all_artifact_names,
    }
    manifest_path = out_dir / "manifest.json"
    with manifest_path.open("w") as f:
        json.dump(manifest, f, indent=2)
    log.info("[publish] Wrote manifest: %s", manifest_path)

    if missing:
        log.warning("[publish] %d artifact(s) were missing (see above).", len(missing))
    else:
        log.info("[publish] All artifacts published successfully to %s", out_dir)

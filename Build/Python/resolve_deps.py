"""Stage: vcpkg manifest install (ProjectA/B) and dotnet restore (ProjectC/D)."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from .constants import REPO_ROOT, log
from .process import run
from .vcpkg_helpers import write_vcpkg_overlay_triplet_dir


def _run_vcpkg_install(
    vcpkg: Path,
    proj_dir: Path,
    vs_dev_cmd: Path | None,
    vcpkg_root: Path,
    kits_x64_bin: Path | None,
    overlay_dir: Path | None,
    stage: str,
) -> None:
    """Run `vcpkg install` in the manifest directory, with VS dev env if available."""
    proj_dir = proj_dir.resolve()
    vcpkg = vcpkg.resolve()
    overlay_arg = ""
    if overlay_dir is not None:
        overlay_arg = f' --overlay-triplets "{overlay_dir}"'
    vcpkg_cmd = f'call "{vcpkg}" install --triplet x64-windows{overlay_arg} || exit /b 1'
    if vs_dev_cmd is not None and vs_dev_cmd.exists():
        lines = [
            "@echo off",
            "setlocal EnableExtensions",
            f'call "{vs_dev_cmd}" -arch=x64 -host_arch=x64 || exit /b 1',
            f'set "VCPKG_ROOT={vcpkg_root}"',
            'set "VCPKG_DEFAULT_TRIPLET=x64-windows"',
        ]
        if kits_x64_bin is not None and kits_x64_bin.is_dir():
            lines.append(f'set "PATH={kits_x64_bin};%PATH%"')
        lines.extend(
            [
                f'cd /d "{proj_dir}"',
                vcpkg_cmd,
            ]
        )
        fd, bat_path_str = tempfile.mkstemp(suffix=".bat", text=True)
        os.close(fd)
        bat_path = Path(bat_path_str)
        try:
            bat_text = "\r\n".join(lines) + "\r\n"
            bat_path.write_text(bat_text, encoding="utf-8")
            log.info("[%s] VsDevCmd wrapper batch:\n%s", stage, bat_text.rstrip())
            run(["cmd.exe", "/c", str(bat_path)], cwd=proj_dir, stage=stage)
        finally:
            try:
                bat_path.unlink()
            except OSError:
                pass
    else:
        cmd = [str(vcpkg), "install", "--triplet", "x64-windows"]
        if overlay_dir is not None:
            cmd += ["--overlay-triplets", str(overlay_dir)]
        run(cmd, cwd=proj_dir, stage=stage)


def stage_resolve_deps(tools: dict, cfg: dict) -> None:  # noqa: ARG001
    log.info("[resolve_deps] Starting dependency resolution...")

    vcpkg: Path = tools["vcpkg"]
    vs_dev_cmd: Path | None = tools.get("vs_dev_cmd")
    dotnet: Path = tools["dotnet"]
    vcpkg_root = vcpkg.parent
    kits_x64 = tools.get("windows_kits_x64_bin")

    overlay_dir: Path | None = None
    if sys.platform == "win32":
        overlay_dir = write_vcpkg_overlay_triplet_dir()
        if overlay_dir is None:
            log.error(
                "[resolve_deps] Could not write vcpkg overlay triplet (Windows SDK / rc.exe). "
                "Install the Windows 10/11 SDK with Visual Studio Installer."
            )
            sys.exit(1)

    for proj_name in ("ProjectA", "ProjectB"):
        proj_dir = REPO_ROOT / proj_name
        log.info("[resolve_deps] vcpkg install for %s", proj_name)
        _run_vcpkg_install(
            vcpkg, proj_dir, vs_dev_cmd, vcpkg_root, kits_x64, overlay_dir, "resolve_deps"
        )

    for proj_name in ("ProjectC", "ProjectD"):
        sln_path = REPO_ROOT / proj_name / f"{proj_name}.sln"
        log.info("[resolve_deps] dotnet restore for %s", proj_name)
        run(
            [str(dotnet), "restore", str(sln_path)],
            stage="resolve_deps",
        )

    log.info("[resolve_deps] All dependencies resolved.")

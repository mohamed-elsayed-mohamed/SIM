"""Locate MSBuild, vcpkg, dotnet, Unity, and related Windows tooling."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import winreg
from pathlib import Path

from .constants import log
from .vcpkg_helpers import find_windows_kits_x64_bin


def detect_msbuild() -> Path:
    """Locate MSBuild via vswhere (requires Visual Studio 2022)."""
    vswhere = Path(
        os.environ.get(
            "ProgramFiles(x86)",
            r"C:\Program Files (x86)",
        )
    ) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"

    if not vswhere.exists():
        log.error(
            "vswhere.exe not found at %s. "
            "Install Visual Studio 2022 from https://visualstudio.microsoft.com/downloads/",
            vswhere,
        )
        sys.exit(1)

    result = subprocess.run(
        [
            str(vswhere),
            "-latest",
            "-requires", "Microsoft.Component.MSBuild",
            "-find", r"MSBuild\**\Bin\MSBuild.exe",
        ],
        capture_output=True,
        text=True,
    )
    paths = [p.strip() for p in result.stdout.splitlines() if p.strip()]
    if not paths:
        log.error(
            "MSBuild not found via vswhere. "
            "Install 'Desktop development with C++' workload in Visual Studio 2022."
        )
        sys.exit(1)
    return Path(paths[0])


def detect_vs_dev_cmd() -> Path | None:
    """
    Locate VsDevCmd.bat so we can run vcpkg (CMake/Ninja) with the same env as
    the "Developer Command Prompt" (INCLUDE/LIB/PATH including Windows SDK rc.exe).
    vcvars64.bat alone is often insufficient for CMake's vs_link_exe + Ninja.
    """
    vswhere = Path(
        os.environ.get(
            "ProgramFiles(x86)",
            r"C:\Program Files (x86)",
        )
    ) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"

    if not vswhere.exists():
        return None

    result = subprocess.run(
        [
            str(vswhere),
            "-latest",
            "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
            "-property", "installationPath",
        ],
        capture_output=True,
        text=True,
    )
    line = result.stdout.strip().splitlines()
    if not line or not line[0].strip():
        return None

    vsdevcmd = Path(line[0].strip()) / "Common7" / "Tools" / "VsDevCmd.bat"
    return vsdevcmd if vsdevcmd.exists() else None


def detect_vcpkg(config_vcpkg_root: str) -> Path:
    """Locate vcpkg executable. Checks config, env var, then common paths."""
    candidates = []

    if config_vcpkg_root:
        candidates.append(Path(config_vcpkg_root) / "vcpkg.exe")

    env_root = os.environ.get("VCPKG_ROOT", "")
    if env_root:
        candidates.append(Path(env_root) / "vcpkg.exe")

    for common in [r"C:\vcpkg", r"C:\src\vcpkg", r"C:\tools\vcpkg"]:
        candidates.append(Path(common) / "vcpkg.exe")

    for candidate in candidates:
        if candidate.exists():
            return candidate

    log.error(
        "vcpkg.exe not found. "
        "Install vcpkg from https://vcpkg.io/en/getting-started and set VCPKG_ROOT, "
        "or set 'vcpkg_root' in build_config.json."
    )
    sys.exit(1)


def detect_dotnet() -> Path:
    """Locate the dotnet CLI."""
    dotnet = shutil.which("dotnet")
    if dotnet:
        return Path(dotnet)
    log.error(
        "dotnet CLI not found on PATH. "
        "Install .NET 8 SDK from https://dotnet.microsoft.com/download"
    )
    sys.exit(1)


def detect_unity(config_unity_editor: str) -> Path | None:
    """
    Locate Unity Editor executable.
    Returns None if not found (Unity build stage will be skipped with a warning).
    """
    candidates = []

    if config_unity_editor:
        candidates.append(Path(config_unity_editor))

    env_unity = os.environ.get("UNITY_EDITOR", "")
    if env_unity:
        candidates.append(Path(env_unity))

    # Check Unity Hub registry key for installed editors
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Unity Technologies\Installed Editors",
        )
        i = 0
        while True:
            try:
                name, _, _ = winreg.EnumValue(key, i)
                # Registry value names are version strings like "2022.3.20f1"
                subkey = winreg.OpenKey(key, name)
                editor_path, _ = winreg.QueryValueEx(subkey, "Path")
                candidates.append(Path(editor_path) / "Unity.exe")
                i += 1
            except OSError:
                break
    except OSError:
        pass

    # Common Unity Hub installation paths
    for base in [
        r"C:\Program Files\Unity\Hub\Editor",
        r"C:\Program Files (x86)\Unity\Hub\Editor",
    ]:
        base_path = Path(base)
        if base_path.exists():
            for version_dir in sorted(base_path.iterdir(), reverse=True):
                candidates.append(version_dir / "Editor" / "Unity.exe")

    for candidate in candidates:
        if candidate.exists():
            return candidate

    log.warning(
        "Unity Editor not found. ProjectE (Unity) build will be SKIPPED. "
        "Install Unity 2022.3 LTS via Unity Hub from https://unity.com/download, "
        "then set UNITY_EDITOR or 'unity_editor' in build_config.json."
    )
    return None


def detect_tools(cfg: dict) -> dict:
    """Run all tool detections. Returns a dict of resolved paths."""
    log.info("[detect] Detecting build tools...")

    msbuild = (
        Path(cfg["msbuild"])
        if cfg.get("msbuild")
        else detect_msbuild()
    )
    log.info("[detect] MSBuild:  %s", msbuild)

    vcpkg = detect_vcpkg(cfg.get("vcpkg_root", ""))
    log.info("[detect] VCPKG:    %s", vcpkg)

    vs_dev_cmd = detect_vs_dev_cmd()
    if vs_dev_cmd:
        log.info("[detect] VsDevCmd: %s", vs_dev_cmd)
    else:
        log.warning(
            "[detect] VsDevCmd.bat not found — vcpkg install may fail without VS C++ tools"
        )

    kits_x64 = find_windows_kits_x64_bin()
    if kits_x64:
        log.info("[detect] Windows SDK bin (x64): %s", kits_x64)
    else:
        log.warning("[detect] Windows Kits rc.exe path not found — vcpkg may fail at CMake configure")

    dotnet = detect_dotnet()
    log.info("[detect] dotnet:   %s", dotnet)

    unity = detect_unity(cfg.get("unity_editor", ""))
    if unity:
        log.info("[detect] Unity:    %s", unity)
    else:
        log.warning("[detect] Unity:    NOT FOUND — ProjectE will be skipped")

    return {
        "msbuild": msbuild,
        "vcpkg": vcpkg,
        "vs_dev_cmd": vs_dev_cmd,
        "windows_kits_x64_bin": kits_x64,
        "dotnet": dotnet,
        "unity": unity,
    }

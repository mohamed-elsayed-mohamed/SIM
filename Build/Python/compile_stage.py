"""Stage: MSBuild (A/B), dotnet build (C/D), optional Unity player build (E)."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from .constants import REPO_ROOT, log
from .process import run


def stage_compile(tools: dict, cfg: dict) -> None:
    log.info("[compile] Starting compilation...")

    msbuild: Path = tools["msbuild"]
    dotnet: Path = tools["dotnet"]
    unity: Path | None = tools["unity"]
    build_config: str = cfg["config"]
    platform: str = cfg["platform"]

    msbuild_common = [
        f"/p:Configuration={build_config}",
        f"/p:Platform={platform}",
        "/m",           # parallel build
        "/nologo",
        "/verbosity:minimal",
    ]

    # --- Project A (C++ DLL) ---
    log.info("[compile] Building ProjectA...")
    run(
        [str(msbuild), str(REPO_ROOT / "ProjectA" / "ProjectA.sln")] + msbuild_common,
        stage="compile",
    )

    # --- Project B (C++ DLL, depends on A's output) ---
    # Ensure ProjectA.dll is beside ProjectB before linking
    _copy_a_for_b_link(cfg)
    log.info("[compile] Building ProjectB...")
    run(
        [str(msbuild), str(REPO_ROOT / "ProjectB" / "ProjectB.sln")] + msbuild_common,
        stage="compile",
    )

    # --- Project C (C# net8.0) ---
    log.info("[compile] Building ProjectC...")
    run(
        [
            str(dotnet), "build",
            str(REPO_ROOT / "ProjectC" / "ProjectC.sln"),
            "-c", build_config,
            "--no-restore",
        ],
        stage="compile",
    )

    # --- Project D (C# net8.0 + netstandard2.1) ---
    # For the netstandard2.1 TFM we need ProjectC.dll in ProjectD/lib/
    _copy_c_for_d_netstandard(cfg)
    log.info("[compile] Building ProjectD...")
    run(
        [
            str(dotnet), "build",
            str(REPO_ROOT / "ProjectD" / "ProjectD.sln"),
            "-c", build_config,
            "--no-restore",
        ],
        stage="compile",
    )

    # --- Project E (Unity) — optional ---
    if unity:
        log.info("[compile] Building ProjectE (Unity)...")
        _build_unity(tools, unity, cfg)
    else:
        log.warning("[compile] Skipping ProjectE — Unity Editor not found.")

    log.info("[compile] All projects compiled successfully.")


def _copy_a_for_b_link(cfg: dict) -> None:
    """
    Copy ProjectA.dll next to ProjectB's output directory so the linker can
    find ProjectA.lib and the runtime loader finds ProjectA.dll at test time.
    This mirrors what the publish step does but scoped to the build tree.
    """
    # MSBuild places outputs under ProjectA/x64/Release (solution-relative).
    src_dir = REPO_ROOT / "ProjectA" / cfg["platform"] / cfg["config"]
    dst_dir = REPO_ROOT / "ProjectB" / cfg["platform"] / cfg["config"]
    dst_dir.mkdir(parents=True, exist_ok=True)
    for fname in ("ProjectA.dll", "ProjectA.lib"):
        src = src_dir / fname
        if src.exists():
            shutil.copy2(src, dst_dir / fname)
            log.info("[compile] Copied %s → %s", src, dst_dir)


def _copy_c_for_d_netstandard(cfg: dict) -> None:
    """
    ProjectD's netstandard2.1 TFM references ProjectC.dll via a HintPath
    (ProjectD/lib/ProjectC.dll).  Copy the net8.0 output there;
    it is binary-compatible with netstandard2.1 for Unity's purposes.
    """
    src = (
        REPO_ROOT
        / "ProjectC"
        / "bin" / cfg["config"] / "net8.0"
        / "ProjectC.dll"
    )
    lib_dir = REPO_ROOT / "ProjectD" / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copy2(src, lib_dir / "ProjectC.dll")
        log.info("[compile] Copied ProjectC.dll → %s", lib_dir)
    else:
        log.error("[compile] ProjectC.dll not found at %s — did ProjectC build succeed?", src)
        sys.exit(1)


def _sync_unity_bundle_version(cfg: dict) -> None:
    """
    Set PlayerSettings.bundleVersion in ProjectSettings.asset to match the
    pipeline semver (--version / build_config.json) so the built player reports
    the same version as artifacts.
    """
    path = REPO_ROOT / "ProjectE" / "ProjectSettings" / "ProjectSettings.asset"
    version = str(cfg["version"]).strip()
    if not path.exists():
        log.warning("[compile] ProjectSettings.asset not found — skipping bundleVersion sync")
        return
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []
    replaced = False
    for line in lines:
        if line.lstrip().startswith("bundleVersion:"):
            indent = line[: len(line) - len(line.lstrip())]
            out.append(f"{indent}bundleVersion: {version}\n")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out = []
        inserted = False
        for line in lines:
            out.append(line)
            if not inserted and line.lstrip().startswith("productName:"):
                indent = line[: len(line) - len(line.lstrip())]
                out.append(f"{indent}bundleVersion: {version}\n")
                inserted = True
        if not inserted:
            log.error("[compile] Could not set bundleVersion: no productName in ProjectSettings.asset")
            sys.exit(1)
    path.write_text("".join(out), encoding="utf-8")
    log.info("[compile] Unity PlayerSettings bundleVersion = %s", version)


def _build_unity(tools: dict, unity: Path, cfg: dict) -> None:
    project_path = REPO_ROOT / "ProjectE"
    build_output = REPO_ROOT / "ProjectE" / "Builds" / "StandaloneWindows64"

    _sync_unity_bundle_version(cfg)

    # Copy DLLs into Assets/Plugins/ before Unity build
    _copy_dlls_to_unity_plugins(tools, cfg)

    run(
        [
            str(unity),
            "-batchmode",
            "-quit",
            "-projectPath", str(project_path),
            "-buildTarget", "StandaloneWindows64",
            "-buildWindows64Player", str(build_output / "ProjectE.exe"),
            "-logFile", str(REPO_ROOT / "ProjectE" / "unity_build.log"),
        ],
        stage="compile",
    )


def _copy_dlls_to_unity_plugins(tools: dict, cfg: dict) -> None:
    """
    Copy native + managed DLLs into Unity's Assets/Plugins/ folder.

    Uses `dotnet publish` for ProjectC and ProjectD so NuGet dependencies
    (Newtonsoft.Json, Serilog, etc.) are present — Unity resolves referenced
    assemblies next to the plugin DLLs at player build time.
    """
    dotnet: Path = tools["dotnet"]
    plugins_dir = REPO_ROOT / "ProjectE" / "Assets" / "Plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)

    staging = REPO_ROOT / ".unity_plugin_staging" / cfg["config"]
    staging.mkdir(parents=True, exist_ok=True)

    log.info("[compile] dotnet publish → staging (netstandard2.1 ProjectD)...")
    run(
        [
            str(dotnet),
            "publish",
            str(REPO_ROOT / "ProjectD" / "ProjectD.csproj"),
            "-c",
            cfg["config"],
            "-f",
            "netstandard2.1",
            "-o",
            str(staging),
            "--no-restore",
        ],
        stage="compile",
    )
    log.info("[compile] dotnet publish → staging (netstandard2.1 ProjectC, Newtonsoft.Json)...")
    run(
        [
            str(dotnet),
            "publish",
            str(REPO_ROOT / "ProjectC" / "ProjectC.csproj"),
            "-c",
            cfg["config"],
            "-f",
            "netstandard2.1",
            "-o",
            str(staging),
            "--no-restore",
        ],
        stage="compile",
    )

    for dll in sorted(staging.glob("*.dll")):
        shutil.copy2(dll, plugins_dir / dll.name)
        log.info("[compile] DLL → Plugins: %s", dll.name)

    cpp_out = REPO_ROOT / "ProjectA" / cfg["platform"] / cfg["config"]
    cpp_b_out = REPO_ROOT / "ProjectB" / cfg["platform"] / cfg["config"]

    native_copies = [
        (cpp_out / "ProjectA.dll", plugins_dir / "ProjectA.dll"),
        (cpp_b_out / "ProjectB.dll", plugins_dir / "ProjectB.dll"),
        (cpp_out / "fmt.dll", plugins_dir / "fmt.dll"),
    ]
    for src, dst in native_copies:
        if src.exists():
            shutil.copy2(src, dst)
            log.info("[compile] DLL → Plugins: %s", dst.name)
        else:
            log.warning("[compile] DLL not found (skipping): %s", src)

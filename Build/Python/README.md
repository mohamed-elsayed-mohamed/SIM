# Build pipeline (Python)

This folder holds the modular implementation of the multi-project build. The **entry point** is `Build/Python/build.py`, which runs `Build.Python.pipeline.main()`.

## Brief steps

1. **Parse CLI** — Read `--config`, `--version`, `--platform`, `--artifact-repo`, and optional `--write-overlay-triplet` (CI: generates `vcpkg-triplets/x64-windows.cmake` before `vcpkg install`).
2. **Load config** — Merge `build_config.json` with CLI overrides (`config.py`).
3. **Detect tools** — Resolve MSBuild, vcpkg, dotnet, Unity (optional), Windows SDK paths (`tool_detection.py`, `vcpkg_helpers.py`).
4. **Resolve dependencies** — On Windows, writes overlay triplet then `vcpkg install --overlay-triplets …` for ProjectA/B; `dotnet restore` for ProjectC/D (`resolve_deps.py`, `vcpkg_helpers.py`).
5. **Compile** — MSBuild A→B, dotnet build C→D, optional Unity player build for ProjectE (`compile_stage.py`).
6. **Pack** — `dotnet pack` for **SIM.ProjectC** and **SIM.ProjectD** with `--version` as `PackageVersion` (`pack_stage.py`).
7. **Publish** — Copy versioned DLLs, `.nupkg`, and optional Unity output into `<artifact_repo>/Python/<version>_<timestamp>/` and write `manifest.json` (`publish_stage.py`).

## Module map

| Module | Role |
|--------|------|
| `constants.py` | `REPO_ROOT`, logging setup |
| `process.py` | Subprocess runner with logging |
| `vcpkg_helpers.py` | Overlay triplet (`write_vcpkg_overlay_triplet_dir`) + Windows Kits bin |
| `tool_detection.py` | Locate build tools |
| `config.py` | `build_config.json` + CLI merge |
| `resolve_deps.py` | vcpkg + restore |
| `compile_stage.py` | Build and Unity steps |
| `pack_stage.py` | `dotnet pack` for C/D NuGet packages |
| `publish_stage.py` | Artifacts + manifest |
| `pipeline.py` | `parse_args`, `main` |

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

This is a DevOps Contractor Case Study implementing a multi-language build pipeline for candidate evaluation. The goal is a fully automated, end-to-end pipeline across C++, C#, and Unity projects with dependency management and artifact publishing.

## Repository Layout (to be created)

```
/
├── ProjectA/          # C++ static/dynamic library (base, no upstream deps) — VCPKG
├── ProjectB/          # C++ static/dynamic library (consumes ProjectA) — VCPKG
├── ProjectC/          # C# class library .NET (consumes ProjectB via interop) — NuGet
├── ProjectD/          # C# class library .NET (consumes ProjectC) — NuGet
├── ProjectE/          # Unity application (consumes ProjectD) — UPM or NuGet
├── Build/Python/build.py  # Single entry point for the full pipeline
├── build_config.json  # Optional config file for platform/configuration defaults
└── README.md            # Architecture, design decisions, trade-offs, production path
```

Each project is a separate Visual Studio solution (`.sln`). Projects use "hello world" / pass-through logic — complexity is in the pipeline, not the application logic.

## Dependency Chain

```
Project A (C++) → Project B (C++) → Project C (C#) → Project D (C#) → Project E (Unity)
```

- **A & B**: VCPKG manifest mode (`vcpkg.json`) — each declares at least one external package (e.g., `fmt`, `nlohmann-json`)
- **C & D**: NuGet via `<PackageReference>` in `.csproj` — each references at least one package (e.g., `Newtonsoft.Json`, `Serilog`)
- **E**: Unity Package Manager (UPM) or NuGet for Unity
- **Interop boundary B→C**: Must be explicitly handled and documented — P/Invoke (native DLL export) is the simplest approach on Windows

## Build Script

### Entry Point

```bash
python Build/Python/build.py --config Release --version 1.0.0
python Build/Python/build.py --config Debug   --version 1.0.0 --platform x64
```

### Pipeline Order

The script executes these stages in order, halting with a non-zero exit code on any failure:

1. **Dependency resolution**: VCPKG install for A & B, `nuget restore` for C & D, Unity package resolution for E
2. **Compilation** (in dependency order): A → B → C → D → E — uses MSBuild via `subprocess`
3. **Artifact publishing**: Upload versioned binaries/packages to the configured artifact repository

### Script Requirements

- Python 3.9+
- Uses `subprocess` for all tool invocations (no shell script wrappers)
- Structured logging at each step (start, success/failure)
- Target platform and build config via CLI args or `build_config.json`
- Exits non-zero on any failure

## Build Environment

- **OS**: Windows (primary)
- **Compiler**: Visual Studio 2022 / MSBuild (`MSBuild.exe`)
- **C++ deps**: VCPKG in manifest mode (preferred over classic mode for reproducibility)
- **C# deps**: NuGet CLI or `dotnet restore`
- **Unity**: Unity Editor CLI (`-batchmode -quit -buildTarget`)

## Key Design Decisions to Document

The `README.md` architecture summary must cover:

- Why manifest mode over classic mode for VCPKG
- Chosen C++/C# interop approach (P/Invoke, C++/CLI, COM) and why
- Artifact repository choice (local file share, NuGet feed, GitHub Packages, etc.)
- Versioning strategy (semver passed as `--version` arg)
- What would change for production: CI/CD integration, secrets management, parallel builds

## Deliverables Checklist

- [ ] All five Visual Studio solutions with source code and config
- [ ] `build.py` running end-to-end without manual intervention
- [ ] Architecture diagram (dependency chain + dep managers + pipeline flow + artifact targets)
- [ ] Brief written summary of design decisions and trade-offs
- [ ] (Bonus) GitHub Actions or Azure Pipelines CI/CD workflow

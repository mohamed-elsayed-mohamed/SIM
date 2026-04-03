# SIM — DevOps case study

Multi-language build pipeline (C++ → C# → Unity) with VCPKG, NuGet, UPM, and local plus CI artifact publishing.

### Three build entry points (Python, Docker, GitHub)

| Type | How you run it | Output / notes |
|------|----------------|----------------|
| **Python (host)** | `python Build/Python/build.py …` (CLI args) or `RunBuild.bat` | Same pipeline on your machine; reads `build_config.json`; publishes to `artifacts/Python/<version>_<timestamp>/` with `manifest.json`. |
| **Docker** | `RunDockerBuild.bat` → `docker compose -f Build/Docker/docker-compose.yml up --build` | Windows **containers** only (Docker Desktop → *Switch to Windows containers*); reproducible toolchain inside the image; artifacts under `./artifacts` (see script output). |
| **GitHub Actions** | Push or PR to `main` runs `.github/workflows/build.yml` | Hosted CI: composite actions under `.github/actions/`; `artifacts/<run_number>/`, NuGet pack/push to GitHub Packages on **push to `main`** only; Unity player build skipped on `windows-latest` (DLLs still staged for ProjectE). |

---

## 1. Architecture diagram

**Visual UI (browser):** open [`docs/architecture.html`](docs/architecture.html) for the same workflow layout (ASCII + build tree + artifact targets).

**§1** covers: **Dependency & data flow** (ASCII workflow below), **artifact repository targets** (table), then reference tables and **Pipeline detail** (`build.py` stage tree). The **resolve → compile → publish** order is in **Pipeline detail** and in `docs/architecture.html`.

### 1.A Dependency & data flow (workflow)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Dependency & Data Flow                            │
└──────────────────────────────────────────────────────────────────────────┘

  ┌──────────────┐   links    ┌──────────────┐  P/Invoke   ┌──────────────┐
  │  Project A   │ ─────────▶ │  Project B   │ ──────────▶ │  Project C   │
  │  C++ DLL     │            │  C++ DLL     │             │  C# net8.0   │
  │  fmt (VCPKG) │            │  nlohmann    │             │  Newtonsoft  │
  │              │            │  -json       │             │  .Json       │
  └──────────────┘            └──────────────┘             └──────┬───────┘
                                                                  │ project ref
                                                                  ▼
                                                          ┌──────────────┐
                                                          │  Project D   │
                                                          │  C# net8.0 + │
                                                          │  netstandard2.1 │
                                                          │  Serilog     │
                                                          └──────┬───────┘
                                                                 │ DLL copy
                                                                 ▼
                                                         ┌───────────────┐
                                                         │  Project E    │
                                                         │  Unity (UPM)  │
                                                         │  Newtonsoft   │
                                                         └───────────────┘
```

**Managers per layer:** A/B — **vcpkg** (manifest); C/D — **NuGet**; E — **UPM**.

### 1.B Artifact repository targets (after publish)

The **publish** step (local `build.py` or CI) produces or uploads to:

| Target | What goes there |
|--------|-----------------|
| **Local / Python** | `<artifact_repo>/Python/<version>_<timestamp>/` (from `build_config.json`; default under `./artifacts`) |
| **CI artifact folder** | `artifacts/<run_number>/` plus `manifest.json` from the workflow |
| **GitHub Packages (NuGet)** | **SIM.ProjectC**, **SIM.ProjectD** — push on push to `main` using `GITHUB_TOKEN` |
| **Optional second feed** | Same `.nupkg` files if repo secrets `NUGET_FEED_URL` and `NUGET_FEED_API_KEY` are set |

**Reading §1**

- **§1.A:** Workflow runs **A → B → C** on one row, then **down** to **D**, then **E** (matches linker/project refs and Unity staging).
- **§1.B:** After publish, outputs land in the **local** drop, **CI** folder, **GitHub Packages**, and optionally a **second NuGet feed**.

### Project & dependency manager reference

| Project | Language | Dep manager | Packages (examples) |
|---------|----------|-------------|---------------------|
| A | C++ | VCPKG (manifest mode) | `fmt` |
| B | C++ | VCPKG (manifest mode) | `nlohmann-json` |
| C | C# | NuGet (`dotnet restore`) | `Newtonsoft.Json 13.x` |
| D | C# | NuGet (`dotnet restore`) | `Serilog 3.x`, `Serilog.Sinks.Console 5.x` |
| E | Unity | UPM (`Packages/manifest.json`) | `com.unity.nuget.newtonsoft-json 3.2.1` |

| Project | `.sln` in repo | Notes |
|---------|----------------|-------|
| A–D | Yes (`ProjectA.sln` … `ProjectD.sln`) | Built with MSBuild / `dotnet` as in the pipeline. |
| E | No committed `.sln` | Unity layout (`Assets/`, `Packages/manifest.json`, `ProjectSettings/`). Automated build uses the Unity CLI, not MSBuild on a solution file. |

**Unity / UPM:** There is no separate `dotnet restore`-style step for UPM in `build.py`. Packages in `Packages/manifest.json` resolve when the Unity Editor runs (batch or interactive).

### Pipeline detail (Python `build.py`)

```
python Build/Python/build.py --config Release --version 1.0.0
        │
        ├─ [load_config]     build_config.json + CLI overrides
        ├─ [detect_tools]    MSBuild, vcpkg, dotnet, Unity (optional)
        ├─ [resolve_deps]    vcpkg install; dotnet restore C,D
        ├─ [compile]         A → B → C → D → E (see diagram)
        └─ [publish]         artifacts/Python/<version>_<timestamp>/ + manifest.json
```

**Build order vs case-study PDF:** The PDF lists **E → D → C → B → A**; that order does not satisfy compile/link dependencies. This repo uses **A → B → C → D → E**, which matches the graph and tooling.

### CI (GitHub Actions) vs local `build.py`

| Aspect | Local `python Build/Python/build.py …` | `.github/workflows/build.yml` + `.github/actions/*` |
|--------|----------------------------------------|------------------------------------------------------|
| Stages | `load_config` → `detect_tools` → `resolve_deps` → `compile` → `publish` | Same logical steps via composite actions |
| Publish output | `artifacts/Python/<version>_<timestamp>/` | `artifacts/<VERSION>/` (`VERSION` = `github.run_number`) |
| NuGet packages | **`dotnet pack`** in `build.py` after compile (`PackageVersion` = `--version`) | CI: same → `1.0.<run_number>` → folder + push |
| Remote feeds | N/A | **GitHub Packages** with `GITHUB_TOKEN`; optional **second feed** via `NUGET_FEED_URL` + `NUGET_FEED_API_KEY` |
| Unity player | Built if Unity is detected | Skipped on `windows-latest`; DLLs still copied to `Assets/Plugins` |

Upload: `actions/upload-artifact` publishes the CI `artifacts/<VERSION>/` folder (DLLs, `manifest.json`, `.nupkg` when present).

---

## 5. Brief documentation & talking points

Short summary (design choices, limitations, production evolution)—about **1–2 pages equivalent** if printed. Use **§5.1–§5.3** as **interview or review talking points**; deeper tables follow each summary.

### 5.1 Design decisions

**Summary:** **VCPKG manifest mode** keeps C++ deps reproducible per project and CI-cacheable. **P/Invoke** (not C++/CLI/COM) keeps one native DLL and works in .NET 8 and Unity IL2CPP/Mono. **Artifacts** default to a **local folder** for Python runs; **CI** adds **NuGet** publishing to **GitHub Packages** (and optionally another feed) for sharing **SIM.ProjectC** / **SIM.ProjectD**. **Versioning:** semver via `--version` for Python; CI uses `github.run_number` for folders and `1.0.<run>` for package versions without patching source.

#### Why VCPKG manifest mode (not classic)?

**Chosen:** Manifest mode (`vcpkg.json` per project).

| | Manifest mode | Classic mode |
|--|--------------|--------------|
| Reproducibility | Each project locks its own dependency set | Global install leaks across projects |
| CI | `vcpkg_installed/` cacheable by `vcpkg.json` hash | No lock file; machine-global installs |
| Onboarding | Clone → `vcpkg install` → build | Developers must know global package set |

Manifest mode is the [vcpkg-recommended approach](https://vcpkg.io/en/docs/maintainers/manifest-files.html) for projects and CI.

#### Why P/Invoke for C++/C#?

**Chosen:** `extern "C" __declspec(dllexport)` + `[DllImport]`.

| Approach | Pros | Cons |
|----------|------|------|
| **P/Invoke** | No mixed-mode DLL; works on .NET + Unity IL2CPP | Marshal lifetime; simple types cross easily |
| C++/CLI | Rich interop | `/clr`; not suitable for Unity IL2CPP |
| COM | Language-neutral | Heavy for a small boundary |

**Interop contract:** `ProjectB` exports `GetJsonGreeting()` → `const char*`; buffer owned by static `std::string` in the DLL (do not free). `ProjectC` uses `Marshal.PtrToStringAnsi`.

#### Artifact targets & versioning

- **Python:** `<artifact_repo>/Python/<version>_<timestamp>/` (from `build_config.json`, default `./artifacts`).
- **CI:** `artifacts/<run_number>/` + NuGet **SIM.ProjectC** / **SIM.ProjectD** to `nuget.pkg.github.com/<owner>/index.json` with `GITHUB_TOKEN`.
- **Optional:** `NUGET_FEED_URL` + `NUGET_FEED_API_KEY` for Azure Artifacts, nuget.org, etc.

| Production-style upgrade | Direction |
|--------------------------|-----------|
| Team-wide binary sharing | UNC, Azure Blob + `azcopy`, etc. |
| Containers | ACR, GHCR |
| Releases | GitHub Releases + `gh release upload` |

`--artifact-repo` / `artifact_repo` changes the **local** drop in one place; CI secrets are set in the repo **Settings → Secrets**.

---

### 5.2 Trade-offs

**Summary:** Multiple **`.sln`** files plus a Unity folder trade a single mega-solution for standard toolchains. **Static string buffers** in native code are simple but not thread-safe. **ProjectD** multi-targets `net8.0` and `netstandard2.1` for Unity at the cost of build time and API surface. **ProjectC** is not multi-targeted, so `build.py` must **copy** `ProjectC.dll` before building D’s `netstandard2.1`. **Local artifacts** are easy but not a long-term enterprise store—**CI NuGet** addresses sharing for managed libs. **Unity optional** keeps the pipeline green without an Editor, but **E** is not always built.

| Decision | Benefit | Cost |
|----------|---------|------|
| Separate solutions A–D; Unity folder for E | MSBuild/`dotnet`/Unity as intended | No single unified `.sln` for all five |
| Static `std::string` in native DLL | No cross-DLL allocator issues | Not thread-safe; pointer stale after next call |
| D: `net8.0;netstandard2.1` | One project for CLI + Unity | Slower build; smaller API on `netstandard2.1` |
| C: single TFM | Simpler `csproj` | HintPath + copy step for D’s `netstandard2.1` ref |
| Local `artifact_repo` | No cloud required | Not durable multi-site storage without CI feeds |
| Unity skipped if absent | A–D still build | E sometimes missing |

---

### 5.3 Production path

**Summary:** **CI/CD** is already sketched via **GitHub Actions** (composite actions mirroring `build.py`). **Secrets:** `GITHUB_TOKEN` suffices for GitHub Packages; add **repo secrets** only for a **second NuGet feed**. Local **NuGet.Config** / env vars for private feeds on dev machines; **Unity license** via Hub for headless builds. **Scaling:** parallelise independent native/managed stages later; **cache** `vcpkg_installed/` in CI; **pin** SDKs with `actions/setup-dotnet` and `setup-msbuild`. For **full production**, add **approval gates**, **environment-specific configs**, **signing**, **SBOM**, and **immutable artifact retention** (blob + retention policies).

#### CI/CD (current repo)

- Workflow: `.github/workflows/build.yml` → `.github/actions/*`.
- Runner: `windows-latest`; Unity **player** skipped in CI; plugin **staging** still runs.
- `permissions`: `contents: read`, `packages: write` for NuGet push.
- `actions/cache` on `vcpkg.json` for **vcpkg** trees.

#### Secrets management

| Scenario | Approach |
|----------|----------|
| GitHub Packages from Actions | `GITHUB_TOKEN` (no extra secret) |
| Second NuGet feed | `NUGET_FEED_URL`, `NUGET_FEED_API_KEY` in repo secrets |
| Local dev, private feeds | `NuGet.Config` / environment variables |
| Unity batch | License via Unity Hub before first CI headless use |
| Config / credentials | Not committed in `build_config.json` |

#### Parallelism & caching

- **A/B** vs **C/D** could run in parallel in a future pipeline (no compile-time cross-language link between those pairs); **E** still gates on **D** outputs.
- Managed packages **SIM.ProjectC** / **SIM.ProjectD** on GitHub Packages give version pins; native **A/B** DLLs may still want a **blob store** or **release assets** for full traceability.

---

## Document map

| Section | Purpose |
|---------|---------|
| **§1** Architecture diagram | ASCII dependency workflow + artifact table; [`docs/architecture.html`](docs/architecture.html); pipeline stages in **Pipeline detail** |
| Following §1 subsections | Tables: projects/managers, `build.py` stage list, CI vs local |
| **§5** Brief documentation & talking points | **§5.1** design decisions, **§5.2** trade-offs, **§5.3** production path (short summaries + detail tables) |

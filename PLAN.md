# DevOps Case Study — Implementation Plan

## Decisions Locked In

| # | Question | Answer / Decision |
|---|----------|------------------|
| 1 | Unity Editor version/path | Unknown — script detects at runtime, errors with install link if missing |
| 2 | VCPKG installed? | Unknown — script detects at runtime, errors with install link if missing |
| 3 | Visual Studio 2022 type | Unknown — script auto-detects via `vswhere.exe` |
| 4 | NuGet CLI on PATH | Yes — available |
| 5 | Restore tool for C & D | `dotnet restore` |
| 6 | .NET target framework | `net8.0` for Projects C & D |
| 7 | Artifact repository | Local folder (`./artifacts/`) |
| 8 | Library type for A & B | Dynamic (`.dll`) — simplest for P/Invoke interop |
| 9 | Bonus CI/CD | Yes — GitHub Actions workflow |

---

## Suggested Packages (Final)

| Project | Language | Package | Manager | Purpose |
|---------|---------|---------|---------|---------|
| A | C++ | `fmt` | VCPKG | String formatting, proves VCPKG manifest mode works |
| B | C++ | `nlohmann-json` | VCPKG | JSON — data serialized before crossing to C# |
| C | C# | `Newtonsoft.Json` | NuGet | Deserialize JSON from B; net8.0 target |
| D | C# | `Serilog` + `Serilog.Sinks.Console` | NuGet | Structured logging; net8.0 target |
| E | Unity | `com.unity.nuget.newtonsoft-json` | UPM | Official Unity-blessed JSON package |

**Interop B→C**: P/Invoke with `extern "C" __declspec(dllexport)` on a `.dll`. No C++/CLI, no COM.  
**.NET Standard note**: Projects C & D target `net8.0`. For Unity to consume the DLL, either target `netstandard2.1` in a shared lib or copy a pre-built `netstandard2.1` DLL into Unity's `Assets/Plugins/`. Best approach: D targets **both** `net8.0` and `netstandard2.1` via multi-targeting in `.csproj`.

---

## Tool Detection Strategy (for `build.py`)

The script will detect each tool before starting and fail fast with a helpful error message if missing:

| Tool | Detection method | Error message includes |
|------|----------------|----------------------|
| MSBuild | `vswhere.exe` → latest VS2022 install | Link: `https://visualstudio.microsoft.com/downloads/` |
| VCPKG | `VCPKG_ROOT` env var or common paths (`C:\vcpkg`, `C:\src\vcpkg`) | Link: `https://vcpkg.io/en/getting-started` |
| Unity Editor | `UNITY_EDITOR` env var or Unity Hub registry (`HKCU\Software\Unity Technologies`) | Link: `https://unity.com/download` |
| `dotnet` | `where dotnet` | Link: `https://dotnet.microsoft.com/download` |
| Python 3.9+ | Version check at script start | — |

---

## Repository Layout

```
/
├── ProjectA/               # C++ DLL — fmt via VCPKG
│   ├── ProjectA.sln
│   ├── ProjectA/
│   │   ├── vcpkg.json      # declares fmt
│   │   ├── ProjectA.vcxproj
│   │   ├── greeting.h
│   │   └── greeting.cpp
├── ProjectB/               # C++ DLL — nlohmann-json via VCPKG, links ProjectA, exports C ABI
│   ├── ProjectB.sln
│   ├── ProjectB/
│   │   ├── vcpkg.json      # declares nlohmann-json
│   │   ├── ProjectB.vcxproj
│   │   ├── bridge.h
│   │   └── bridge.cpp      # extern "C" __declspec(dllexport) functions
├── ProjectC/               # C# net8.0 — Newtonsoft.Json, P/Invokes ProjectB.dll
│   ├── ProjectC.sln
│   ├── ProjectC/
│   │   ├── ProjectC.csproj
│   │   └── NativeBridge.cs # [DllImport("ProjectB")] wrappers
├── ProjectD/               # C# net8.0 + netstandard2.1 — Serilog, wraps ProjectC
│   ├── ProjectD.sln
│   ├── ProjectD/
│   │   ├── ProjectD.csproj # <TargetFrameworks>net8.0;netstandard2.1</TargetFrameworks>
│   │   └── Pipeline.cs
├── ProjectE/               # Unity application — consumes ProjectD netstandard2.1 DLL
│   ├── Assets/
│   │   ├── Plugins/        # ProjectD.dll, ProjectC.dll, ProjectB.dll copied here
│   │   └── Scripts/
│   │       └── AppEntry.cs # MonoBehaviour calling into ProjectD
│   └── Packages/
│       └── manifest.json   # com.unity.nuget.newtonsoft-json
├── artifacts/              # Published output (versioned subfolders)
│   └── 1.0.0/
│       ├── ProjectA.dll
│       ├── ProjectB.dll
│       ├── ProjectC.dll
│       ├── ProjectD.dll
│       └── ProjectE-StandaloneWindows64.exe (or zip)
├── build.py                # Single pipeline entry point
├── build_config.json       # Default platform/config/paths
├── .github/
│   └── workflows/
│       └── build.yml       # Bonus: GitHub Actions CI/CD
├── README.md               # Design decisions + diagram (architecture)
└── .gitignore
```

---

## Phase-by-Phase Plan

### Phase 1 — Repo Skeleton & Config
- [ ] Create all folder structure as above
- [ ] Write `build_config.json`:
  ```json
  {
    "platform": "x64",
    "config": "Release",
    "artifact_repo": "./artifacts",
    "vcpkg_root": "",
    "unity_editor": "",
    "msbuild": ""
  }
  ```
- [ ] Add `.gitignore` (VCPKG build cache, NuGet packages, Unity Library/, obj/, bin/)

### Phase 2 — Project A (C++ DLL, `fmt`)
- [ ] Create VS2022 solution and `.vcxproj` configured as DLL
- [ ] Add `vcpkg.json` with `fmt` dependency
- [ ] Write `greeting.h` / `greeting.cpp`:
  - `extern "C" __declspec(dllexport) const char* GetGreeting()` returning an `fmt::format()`'d string
- [ ] Manual build test: `msbuild ProjectA.sln /p:Configuration=Release /p:Platform=x64`

### Phase 3 — Project B (C++ DLL, `nlohmann-json`, links A, exports C ABI)
- [ ] Create VS2022 solution and `.vcxproj` configured as DLL
- [ ] Add `vcpkg.json` with `nlohmann-json` dependency
- [ ] Configure `.vcxproj` linker: additional lib dirs → ProjectA output folder, link `ProjectA.lib`
- [ ] Write `bridge.cpp`:
  - Calls `GetGreeting()` from A
  - Serializes result into JSON string using nlohmann-json
  - Exports `extern "C" __declspec(dllexport) const char* GetJsonGreeting()` — this is what C# calls
- [ ] Manual build test

### Phase 4 — Project C (C# net8.0, `Newtonsoft.Json`, P/Invokes B)
- [ ] Create VS2022 solution (or `dotnet new classlib`)
- [ ] `ProjectC.csproj` targets `net8.0`, adds `<PackageReference Include="Newtonsoft.Json" />`
- [ ] Write `NativeBridge.cs` with `[DllImport("ProjectB", CallingConvention=CallingConvention.Cdecl)]`
- [ ] Write `Greeter.cs` that calls `NativeBridge.GetJsonGreeting()`, deserializes with `Newtonsoft.Json`
- [ ] Manual build test: `dotnet restore && dotnet build`

### Phase 5 — Project D (C# net8.0 + netstandard2.1, `Serilog`)
- [ ] Create VS2022 solution
- [ ] `ProjectD.csproj`:
  ```xml
  <TargetFrameworks>net8.0;netstandard2.1</TargetFrameworks>
  ```
  Add `Serilog` + `Serilog.Sinks.Console` package references
  Reference ProjectC DLL output
- [ ] Write `Pipeline.cs` — calls ProjectC, logs result via Serilog
- [ ] Manual build test — verify both TFM outputs exist in `bin/`

### Phase 6 — Project E (Unity, consumes D)
- [ ] Create Unity project via Unity Hub (any 2022.3 LTS or 6.x)
- [ ] Edit `Packages/manifest.json` to add `com.unity.nuget.newtonsoft-json`
- [ ] Copy `ProjectD (netstandard2.1).dll`, `ProjectC.dll` into `Assets/Plugins/`
- [ ] Copy `ProjectB.dll` into `Assets/Plugins/` (needed at runtime for P/Invoke)
- [ ] Write `Assets/Scripts/AppEntry.cs` — a `MonoBehaviour.Start()` calling into ProjectD
- [ ] Configure Unity build target: `StandaloneWindows64`
- [ ] Test Unity CLI build manually

### Phase 7 — `build.py` Pipeline Script

```
build.py
  ├── detect_tools()        — vswhere, vcpkg, unity, dotnet; fail fast with links
  ├── load_config()         — merge build_config.json + CLI args
  ├── stage_resolve_deps()  — vcpkg install A,B; dotnet restore C,D; unity UPM (manifest copy)
  ├── stage_compile()       — MSBuild A→B→C→D; Unity CLI E
  ├── stage_publish()       — copy outputs to artifacts/<version>/
  └── main()                — orchestrates stages, structured logging, sys.exit(1) on failure
```

- [ ] CLI: `--config`, `--version`, `--platform`, `--artifact-repo` (all override `build_config.json`)
- [ ] Logging: `logging` module, format: `[TIMESTAMP] [STAGE] message`
- [ ] Each subprocess call: log command, capture stdout/stderr, raise on non-zero returncode
- [ ] `detect_tools()` errors include install URLs, exit code 1
- [ ] Publish stage: create `artifacts/<version>/` folder, copy all `.dll`, `.exe`, Unity build output

### Phase 8 — Documentation (`README.md` architecture sections)
- [ ] Dependency chain diagram (ASCII or embedded image)
- [ ] Design decisions section:
  - VCPKG manifest mode vs classic mode
  - Why P/Invoke over C++/CLI or COM
  - Why local folder artifact repo (and what to swap for production)
  - Versioning strategy (semver via `--version` arg)
- [ ] Trade-offs section
- [ ] Production path section (CI/CD, secrets, parallel builds, artifact caching)

### Phase 9 — GitHub Actions Bonus (`.github/workflows/build.yml`)
- [ ] Trigger: `push` to `main`, `pull_request`
- [ ] Runner: `windows-latest`
- [ ] Steps:
  1. `actions/checkout`
  2. Setup Python 3.11
  3. Install/restore VCPKG (cache `vcpkg/installed/` with `actions/cache`)
  4. Setup MSBuild (`microsoft/setup-msbuild`)
  5. Setup .NET 8 (`actions/setup-dotnet`)
  6. Install Unity Editor via Unity Hub CLI (or skip E build in CI if no Unity license)
  7. Run `python build.py --config Release --version ${{ github.run_number }}`
  8. Upload artifacts with `actions/upload-artifact`

---

## Critical Path & Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Unity Editor not installed | Blocks Phase 6 & 7 | Script detects early, prints link; install `2022.3 LTS` via Unity Hub |
| VCPKG not installed | Blocks Phase 2 & 3 | Script detects early, prints `https://vcpkg.io/en/getting-started`; install to `C:\vcpkg` |
| `ProjectB.dll` not found at P/Invoke runtime | Phase 4 crash | Always copy `ProjectB.dll` next to `ProjectC.dll` in publish step |
| Unity can't load `net8.0` DLL | Phase 6 broken | ProjectD must produce `netstandard2.1` TFM — that's what Unity can load |
| MSBuild path varies | Script fails silently | Always use `vswhere.exe` from `%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\` |
| Unity license required for CLI `-batchmode` | CI blocker | Personal/free licenses work; Unity Hub must activate before first headless build |

---

## Build Command Reference

```bash
# Full pipeline
python build.py --config Release --version 1.0.0

# Debug build on x64
python build.py --config Debug --version 1.0.0 --platform x64

# Override artifact output folder
python build.py --config Release --version 1.0.0 --artifact-repo C:\MyArtifacts
```

---

## Deliverables Checklist

- [ ] ProjectA — VS solution, C++ DLL, `vcpkg.json` with `fmt`
- [ ] ProjectB — VS solution, C++ DLL, `vcpkg.json` with `nlohmann-json`, exports C ABI
- [ ] ProjectC — VS solution, C# `net8.0`, `Newtonsoft.Json`, P/Invoke wrapper
- [ ] ProjectD — VS solution, C# `net8.0;netstandard2.1`, `Serilog`, wraps C
- [ ] ProjectE — Unity project, UPM `newtonsoft-json`, imports D's `netstandard2.1` DLL
- [ ] `build.py` — runs end-to-end, no manual steps
- [ ] `build_config.json` — default config
- [ ] `README.md` — decisions, diagram, trade-offs, production path
- [ ] `.github/workflows/build.yml` — GitHub Actions CI/CD (bonus)
- [ ] Screen recording of pipeline running end-to-end

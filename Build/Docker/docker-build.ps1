<#
.SYNOPSIS
  Docker build orchestration - full pipeline inside a Windows container.
  Stages: dependency resolution -> compile (A->B->C->D->E) -> publish artifacts -> Inno Setup x64 installer (optional if ISCC in image).
  Mount C:\out (see docker-compose: host ./artifacts) to collect results, including SIM-Setup-x64-<VERSION>.exe when Inno Setup is present.
#>
param(
    [string]$OutRoot  = $(if ($env:OUT_ROOT)        { $env:OUT_ROOT }        else { "C:\out" }),
    [string]$Config   = $(if ($env:BUILD_CONFIG)     { $env:BUILD_CONFIG }    else { "Release" }),
    [string]$Version  = $(if ($env:VERSION)          { $env:VERSION }         else { "1.0.0" }),
    [string]$Platform = $(if ($env:BUILD_PLATFORM)   { $env:BUILD_PLATFORM }  else { "x64" })
)

$ErrorActionPreference = "Stop"
Set-Location "C:\src"

# ---------- logging helpers ----------

$script:PipelineStart = Get-Date
$script:StepNumber    = 0
$script:StepResults   = @()

function Write-Banner {
    param([string]$Text, [ConsoleColor]$Color = 'Cyan')
    $line = '=' * 60
    Write-Host ""
    Write-Host $line -ForegroundColor $Color
    Write-Host "  $Text" -ForegroundColor $Color
    Write-Host $line -ForegroundColor $Color
    Write-Host ""
}

function Write-StageBanner {
    param([int]$Number, [string]$Name)
    $line = '-' * 60
    Write-Host ""
    Write-Host $line -ForegroundColor DarkCyan
    Write-Host "  STAGE $Number : $Name" -ForegroundColor White
    Write-Host $line -ForegroundColor DarkCyan
    Write-Host ""
}

function Write-Info    { param([string]$Msg) Write-Host "  [INFO]  $Msg" -ForegroundColor Gray }
function Write-Success { param([string]$Msg) Write-Host "  [OK]    $Msg" -ForegroundColor Green }
function Write-Warn    { param([string]$Msg) Write-Host "  [WARN]  $Msg" -ForegroundColor Yellow }
function Write-Err     { param([string]$Msg) Write-Host "  [FAIL]  $Msg" -ForegroundColor Red }

function Format-Duration([TimeSpan]$ts) {
    if ($ts.TotalMinutes -ge 1) { return "{0:0}m {1:0.0}s" -f [math]::Floor($ts.TotalMinutes), $ts.Seconds }
    return "{0:0.00}s" -f $ts.TotalSeconds
}

function Format-FileSize([long]$bytes) {
    if ($bytes -ge 1MB) { return "{0:N2} MB" -f ($bytes / 1MB) }
    if ($bytes -ge 1KB) { return "{0:N1} KB" -f ($bytes / 1KB) }
    return "$bytes B"
}

function Step {
    param([string]$Project, [string]$Tool, [string]$Description, [scriptblock]$Action)
    $script:StepNumber++
    $stepLabel = "$Tool $Project"
    $stepStart = Get-Date

    Write-Host ""
    Write-Host ("  [{0}] {1}" -f $script:StepNumber, $stepLabel) -ForegroundColor White -NoNewline
    Write-Host "  $Description" -ForegroundColor DarkGray
    Write-Host ("  " + ("-" * 40)) -ForegroundColor DarkGray

    & $Action

    $elapsed = (Get-Date) - $stepStart
    $elapsedStr = Format-Duration $elapsed

    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
        Write-Err "$stepLabel FAILED (exit code $LASTEXITCODE) after $elapsedStr"
        $script:StepResults += [PSCustomObject]@{
            Step     = $script:StepNumber
            Project  = $Project
            Tool     = $Tool
            Status   = "FAIL"
            Duration = $elapsedStr
            ExitCode = $LASTEXITCODE
        }
        exit $LASTEXITCODE
    }

    Write-Success "$stepLabel completed in $elapsedStr"
    $script:StepResults += [PSCustomObject]@{
        Step     = $script:StepNumber
        Project  = $Project
        Tool     = $Tool
        Status   = "OK"
        Duration = $elapsedStr
        ExitCode = 0
    }
}

function Copy-IfExists([string]$Src, [string]$Dst, [string]$Label) {
    if (Test-Path $Src) {
        Copy-Item $Src $Dst -Force
        $size = Format-FileSize (Get-Item $Dst).Length
        Write-Host "          -> $Label ($size)" -ForegroundColor DarkGreen
    } else {
        Write-Warn "Not found: $Src"
    }
}

# ---------- locate MSBuild ----------

$vsWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (Test-Path $vsWhere) {
    $msbuild = & $vsWhere -latest -requires Microsoft.Component.MSBuild `
        -find 'MSBuild\**\Bin\MSBuild.exe' | Select-Object -First 1
}
if (-not $msbuild -or -not (Test-Path $msbuild)) {
    $msbuild = "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\MSBuild.exe"
}
if (-not (Test-Path $msbuild)) {
    Write-Err "Cannot find MSBuild.exe"
    exit 1
}

# ---------- banner ----------

Write-Banner "SIM Docker Build Pipeline" Cyan
Write-Host "  Configuration : " -NoNewline -ForegroundColor Gray
Write-Host $Config -ForegroundColor White
Write-Host "  Platform      : " -NoNewline -ForegroundColor Gray
Write-Host $Platform -ForegroundColor White
Write-Host "  Version       : " -NoNewline -ForegroundColor Gray
Write-Host $Version -ForegroundColor White
Write-Host "  Output        : " -NoNewline -ForegroundColor Gray
Write-Host $OutRoot -ForegroundColor White
Write-Host "  MSBuild       : " -NoNewline -ForegroundColor Gray
Write-Host $msbuild -ForegroundColor DarkGray
Write-Host "  Started at    : " -NoNewline -ForegroundColor Gray
Write-Host (Get-Date -Format "yyyy-MM-dd HH:mm:ss") -ForegroundColor White
Write-Host ""

$projAOut = "C:\src\ProjectA\$Platform\$Config"
$projBOut = "C:\src\ProjectB\$Platform\$Config"

# ===== STAGE 1: Dependencies =====

Write-StageBanner 1 "DEPENDENCY RESOLUTION"

Step -Project "ProjectC" -Tool "dotnet restore" -Description "Restore NuGet packages" {
    dotnet restore C:\src\ProjectC\ProjectC.csproj
}

Step -Project "ProjectD" -Tool "dotnet restore" -Description "Restore NuGet packages" {
    dotnet restore C:\src\ProjectD\ProjectD.csproj
}

Write-Info "ProjectA/B: vcpkg dependencies resolved automatically via MSBuild (manifest mode)"

# ===== STAGE 2: Compile =====

Write-StageBanner 2 "COMPILATION (A -> B -> C -> D -> E)"

$msbArgs = @(
    "/p:Configuration=$Config",
    "/p:Platform=$Platform",
    "/p:VcpkgEnableManifest=true",
    "/m",
    "/nologo",
    "/verbosity:minimal"
)

Step -Project "ProjectA" -Tool "MSBuild" -Description "C++ static/dynamic library (base)" {
    & $msbuild C:\src\ProjectA\ProjectA.sln @msbArgs
}

# Copy ProjectA outputs so ProjectB can link against them
New-Item -ItemType Directory -Force -Path $projBOut | Out-Null
Copy-IfExists "$projAOut\ProjectA.dll" "$projBOut\ProjectA.dll" "ProjectA.dll -> ProjectB"
Copy-IfExists "$projAOut\ProjectA.lib" "$projBOut\ProjectA.lib" "ProjectA.lib -> ProjectB"

Step -Project "ProjectB" -Tool "MSBuild" -Description "C++ library (consumes ProjectA)" {
    & $msbuild C:\src\ProjectB\ProjectB.sln @msbArgs
}

Step -Project "ProjectC" -Tool "dotnet build" -Description "C# class library (P/Invoke -> ProjectB)" {
    dotnet build C:\src\ProjectC\ProjectC.csproj -c $Config --no-restore
}

# Copy ProjectC.dll to ProjectD/lib for the netstandard2.1 HintPath reference
$projCDll = "C:\src\ProjectC\bin\$Config\net8.0\ProjectC.dll"
New-Item -ItemType Directory -Force -Path C:\src\ProjectD\lib | Out-Null
Copy-IfExists $projCDll "C:\src\ProjectD\lib\ProjectC.dll" "ProjectC.dll -> ProjectD/lib"

Step -Project "ProjectD" -Tool "dotnet build" -Description "C# class library (consumes ProjectC)" {
    dotnet build C:\src\ProjectD\ProjectD.csproj -c $Config --no-restore
}

# ProjectE (Unity) - optional, only when UNITY_EDITOR is set
if ($env:UNITY_EDITOR) {
    Write-Info "Building ProjectE (Unity)..."

    $projectSettings = "C:\src\ProjectE\ProjectSettings\ProjectSettings.asset"
    if (Test-Path $projectSettings) {
        (Get-Content $projectSettings -Raw) -replace 'bundleVersion:.*', "bundleVersion: $Version" |
            Set-Content $projectSettings
        Write-Info "Set Unity bundleVersion = $Version"
    }

    $pluginsDir = "C:\src\ProjectE\Assets\Plugins"
    $stagingDir = "C:\src\.unity_plugin_staging\$Config"
    New-Item -ItemType Directory -Force -Path $pluginsDir, $stagingDir | Out-Null

    Step -Project "ProjectD" -Tool "dotnet publish" -Description "Publish netstandard2.1 for Unity" {
        dotnet publish C:\src\ProjectD\ProjectD.csproj -c $Config -f netstandard2.1 -o $stagingDir --no-restore
    }
    Step -Project "ProjectC" -Tool "dotnet publish" -Description "Publish net8.0 for Unity" {
        dotnet publish C:\src\ProjectC\ProjectC.csproj -c $Config -f net8.0 -o $stagingDir --no-restore
    }

    Get-ChildItem $stagingDir -Filter "*.dll" | ForEach-Object {
        Copy-Item $_.FullName "$pluginsDir\$($_.Name)" -Force
        $size = Format-FileSize $_.Length
        Write-Host "          -> DLL -> Plugins: $($_.Name) ($size)" -ForegroundColor DarkGreen
    }
    Copy-IfExists "$projAOut\ProjectA.dll" "$pluginsDir\ProjectA.dll" "ProjectA.dll -> Plugins"
    Copy-IfExists "$projBOut\ProjectB.dll" "$pluginsDir\ProjectB.dll" "ProjectB.dll -> Plugins"
    Copy-IfExists "$projAOut\fmt.dll"      "$pluginsDir\fmt.dll"      "fmt.dll -> Plugins"

    $buildOutput = "C:\src\ProjectE\Builds\StandaloneWindows64\ProjectE.exe"
    Step -Project "ProjectE" -Tool "Unity" -Description "Build StandaloneWindows64 player" {
        & $env:UNITY_EDITOR -batchmode -quit `
            -projectPath C:\src\ProjectE `
            -buildTarget StandaloneWindows64 `
            -buildWindows64Player $buildOutput `
            -logFile C:\src\ProjectE\unity_build.log
    }
} else {
    Write-Host ""
    Write-Warn "ProjectE - UNITY_EDITOR not set (skipped)"
}

# ===== STAGE 3: Publish Artifacts =====

Write-StageBanner 3 "ARTIFACT PUBLISHING"

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$artifactDir = "$OutRoot\Docker\${Version}_${timestamp}"
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null

Write-Info "Artifact directory: $artifactDir"
Write-Host ""

$artifacts = [ordered]@{
    "$projAOut\ProjectA.dll"                                     = "ProjectA.dll"
    "$projBOut\ProjectB.dll"                                     = "ProjectB.dll"
    "C:\src\ProjectC\bin\$Config\net8.0\ProjectC.dll"            = "ProjectC.dll"
    "C:\src\ProjectD\bin\$Config\net8.0\ProjectD.dll"            = "ProjectD_net8.dll"
    "C:\src\ProjectD\bin\$Config\netstandard2.1\ProjectD.dll"    = "ProjectD_netstandard2.1.dll"
    "C:\src\ProjectE\Builds\StandaloneWindows64\ProjectE.exe"    = "ProjectE-StandaloneWindows64.exe"
}

$published = @()
$totalSize = [long]0
foreach ($src in $artifacts.Keys) {
    $name = $artifacts[$src]
    if (Test-Path $src) {
        Copy-Item $src "$artifactDir\$name" -Force
        $fileInfo = Get-Item "$artifactDir\$name"
        $size = Format-FileSize $fileInfo.Length
        $totalSize += $fileInfo.Length
        $published += $name
        Write-Host "  [PUBLISH] " -NoNewline -ForegroundColor Green
        Write-Host $name -NoNewline -ForegroundColor White
        Write-Host "  ($size)" -ForegroundColor DarkGray
    } else {
        Write-Host "  [MISSING] " -NoNewline -ForegroundColor Yellow
        Write-Host $name -NoNewline -ForegroundColor DarkYellow
        Write-Host "  (source not found)" -ForegroundColor DarkGray
    }
}

@{ version = $Version; config = $Config; platform = $Platform; artifacts = $published } |
    ConvertTo-Json | Set-Content "$artifactDir\manifest.json"
Write-Info "Wrote manifest.json"

# Copy Unity player build (if present) — same folder name as Python publish (SIM-Setup.iss)
$unityBuild = "C:\src\ProjectE\Builds\StandaloneWindows64"
if (Test-Path $unityBuild) {
    $unityArtifactDir = "$artifactDir\ProjectE-StandaloneWindows64"
    if (Test-Path $unityArtifactDir) { Remove-Item $unityArtifactDir -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $unityArtifactDir | Out-Null
    Get-ChildItem $unityBuild | ForEach-Object {
        Copy-Item $_.FullName (Join-Path $unityArtifactDir $_.Name) -Recurse -Force
    }
    Write-Info "Copied ProjectE player files -> $unityArtifactDir"
}

# ===== STAGE 4: Inno Setup x64 installer (SIM-Setup.iss) =====
# Uses the versioned artifact folder for both StagingDir and InnoOutputDir (no C:\src\artifacts\InnoStaging).

Write-StageBanner 4 "INNO SETUP (x64 installer)"

$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) {
    $iscc = "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
}

if (-not (Test-Path $iscc)) {
    Write-Warn "ISCC.exe not found (Inno Setup missing from image). Skipping installer."
} else {
    $innoFwd = ($artifactDir -replace '\\', '/')
    $iss = "C:\src\Build\InnoSetup\SIM-Setup.iss"
    $isccArgs = @(
        $iss,
        "/DMyAppVersion=$Version",
        "/DStagingDir=$innoFwd",
        "/DInnoOutputDir=$innoFwd",
        "/Q"
    )
    if (Test-Path "$artifactDir\ProjectE-StandaloneWindows64\ProjectE.exe") {
        $isccArgs += "/DIncludeUnity"
        Write-Info "Inno: including Unity player"
    }

    Write-Info "Running: $iscc $($isccArgs -join ' ')"
    & $iscc @isccArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Inno Setup compiler failed (exit $LASTEXITCODE)"
        exit $LASTEXITCODE
    }
    $setupExe = Join-Path $artifactDir "SIM-Setup-x64-$Version.exe"
    if (Test-Path $setupExe) {
        $sz = Format-FileSize (Get-Item $setupExe).Length
        Write-Success "Installer: $setupExe ($sz)"
    } else {
        Write-Warn "Expected installer not found: $setupExe"
    }
}

# ===== Summary =====

$totalElapsed = (Get-Date) - $script:PipelineStart
$totalElapsedStr = Format-Duration $totalElapsed

Write-Host ""
Write-Banner "BUILD SUMMARY" Green

# Step results table
Write-Host "  Step  Project     Tool              Status  Duration" -ForegroundColor White
Write-Host "  ----  ----------  ----------------  ------  --------" -ForegroundColor DarkGray
foreach ($r in $script:StepResults) {
    $statusColor = if ($r.Status -eq 'OK') { 'Green' } else { 'Red' }
    $line = "  {0,-4}  {1,-10}  {2,-16}  " -f $r.Step, $r.Project, $r.Tool
    Write-Host $line -NoNewline -ForegroundColor Gray
    Write-Host ("{0,-6}" -f $r.Status) -NoNewline -ForegroundColor $statusColor
    Write-Host "  $($r.Duration)" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "  Artifacts : " -NoNewline -ForegroundColor Gray
Write-Host "$($published.Count) files" -NoNewline -ForegroundColor White
Write-Host " ($(Format-FileSize $totalSize))" -ForegroundColor DarkGray

Write-Host "  Output    : " -NoNewline -ForegroundColor Gray
Write-Host $artifactDir -ForegroundColor White

Write-Host "  Total time: " -NoNewline -ForegroundColor Gray
Write-Host $totalElapsedStr -ForegroundColor White

Write-Host ""

$failCount = ($script:StepResults | Where-Object { $_.Status -ne 'OK' }).Count
if ($failCount -gt 0) {
    Write-Banner "PIPELINE FAILED ($failCount step(s) failed)" Red
    exit 1
} else {
    Write-Banner "PIPELINE COMPLETE - ALL STEPS PASSED" Green
}

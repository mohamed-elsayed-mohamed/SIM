# escape=`
# Windows container - requires Docker Desktop in "Windows containers" mode.
#
# Build (from repo root):
#   docker build -f Build/Docker/Dockerfile -t sim-pipeline:latest .
#
# Run:
#   docker run --rm -v "${PWD}\Build\Docker\Output:C:\out" -e VERSION=1.0.0 sim-pipeline:latest
#
# If image build fails with: hcsshim::ImportLayer failed ... (0x3)
#   try: docker builder prune -af  then rebuild; ensure Docker Desktop uses Windows containers;
#   ensure enough disk space; temporarily disable AV real-time scan on the Docker data folder.

FROM mcr.microsoft.com/windows/servercore:ltsc2022

SHELL ["powershell", "-Command", "$ErrorActionPreference = 'Stop'; $ProgressPreference = 'SilentlyContinue';"]

# ---------- Visual Studio 2022 Build Tools with C++ ----------
# IMPORTANT: Use Start-Process -Wait (PowerShell wait) + --wait (installer wait).
# The original cmd /S /C wrapper hangs in Windows containers; Start-Process does not.
RUN Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vs_buildtools.exe' -OutFile C:\vs_buildtools.exe; `
    $p = Start-Process -FilePath 'C:\vs_buildtools.exe' -ArgumentList `
        '--quiet','--wait','--norestart','--nocache', `
        '--add','Microsoft.VisualStudio.Workload.VCTools', `
        '--add','Microsoft.VisualStudio.Component.VC.Tools.x86.x64', `
        '--add','Microsoft.VisualStudio.Component.VC.CMake.Project', `
        '--add','Microsoft.VisualStudio.Component.Windows10SDK.20348', `
        '--includeRecommended' `
        -Wait -PassThru; `
    $exitCode = $p.ExitCode; `
    Write-Host "VS Build Tools installer exited with code: $exitCode"; `
    if ($exitCode -ne 0 -and $exitCode -ne 3010) { `
        Write-Host "ERROR: VS Build Tools install failed (exit code $exitCode)"; `
        exit 1 `
    }; `
    Remove-Item C:\vs_buildtools.exe -Force

# Verify the C++ targets actually exist
RUN if (-not (Test-Path 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Microsoft\VC\v170\Microsoft.Cpp.Default.props')) { `
        Write-Host 'ERROR: VC targets not found after install'; `
        Get-ChildItem 'C:\Program Files (x86)\Microsoft Visual Studio' -Recurse -Depth 4 -ErrorAction SilentlyContinue | Select-Object -First 30; `
        exit 1 `
    } else { `
        Write-Host 'OK: VC targets found' `
    }

# ---------- Chocolatey: Git + Python ----------
RUN Set-ExecutionPolicy Bypass -Scope Process -Force; `
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; `
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1')); `
    choco install -y git python311

# ---------- Inno Setup 6 (ISCC) — silent install from GitHub release ----------
# Do NOT use "choco install innosetup" here: on some hosts it contributes to
# hcsshim::ImportLayer failed ... The system cannot find the path specified (0x3)
# when Docker commits the image layer. Official setup + /VERYSILENT matches VS Build Tools.
RUN $url = 'https://github.com/jrsoftware/issrc/releases/download/is-6_7_1/innosetup-6.7.1.exe'; `
    Invoke-WebRequest -Uri $url -OutFile C:\innosetup.exe; `
    $p = Start-Process -FilePath C:\innosetup.exe -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/ALLUSERS' -Wait -PassThru; `
    $code = $p.ExitCode; `
    Remove-Item C:\innosetup.exe -Force; `
    if ($code -ne 0) { Write-Host \"Inno Setup exit code: $code\"; exit 1 }; `
    $iscc = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'; `
    if (-not (Test-Path $iscc)) { Write-Host 'ERROR: ISCC.exe not found'; exit 1 }; `
    Write-Host \"OK: Inno Setup 6 -> $iscc\"

# ---------- .NET 8 SDK ----------
RUN Invoke-WebRequest -Uri 'https://dot.net/v1/dotnet-install.ps1' -OutFile C:\dotnet-install.ps1; `
    & C:\dotnet-install.ps1 -Channel 8.0 -InstallDir C:\dotnet; `
    Remove-Item C:\dotnet-install.ps1 -Force

# ---------- vcpkg at the exact baseline commit ----------
RUN $env:Path = 'C:\Program Files\Git\cmd;' + $env:Path; `
    git config --global --add safe.directory '*'; `
    git clone https://github.com/microsoft/vcpkg.git C:\vcpkg; `
    Set-Location C:\vcpkg; `
    git checkout e80346e570b767219f85dc95e3736853bfec3a70; `
    cmd /c bootstrap-vcpkg.bat -disableMetrics

# ---------- Environment ----------
ENV VCPKG_ROOT=C:\vcpkg `
    VCPKG_DEFAULT_TRIPLET=x64-windows `
    GIT_TERMINAL_PROMPT=0

# Put everything on PATH
RUN $machinePath = [Environment]::GetEnvironmentVariable('Path','Machine'); `
    $extra = @( `
        'C:\Python311', `
        'C:\Python311\Scripts', `
        'C:\Program Files\Git\cmd', `
        'C:\dotnet', `
        'C:\vcpkg', `
        'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin' `
    ) -join ';'; `
    [Environment]::SetEnvironmentVariable('Path', $machinePath + ';' + $extra, 'Machine')

WORKDIR C:\src
COPY . C:\src

ENTRYPOINT ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "C:\\src\\Build\\Docker\\docker-build.ps1"]

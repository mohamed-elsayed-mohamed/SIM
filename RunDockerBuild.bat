@echo off
REM Docker pipeline (NOT RunBuild.bat — that runs Python build.py on the host).
REM Requires Docker Desktop in Windows container mode.
REM Artifacts: Build\Docker\Output

setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo ========================================
echo   SIM - Docker build (Windows image)
echo ========================================
echo.

where docker >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker was not found on PATH.
    echo Install Docker Desktop and start it, then try again.
    goto :fail
)

docker version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker does not respond. Start Docker Desktop and wait until it is running.
    goto :fail
)

set "DOCKER_SERVER_OS="
for /f "usebackq tokens=*" %%O in (`docker version --format "{{.Server.Os}}" 2^>nul`) do set "DOCKER_SERVER_OS=%%O"

if not "%DOCKER_SERVER_OS%"=="" if /I not "%DOCKER_SERVER_OS%"=="windows" (
    echo [ERROR] Docker is in Linux container mode. This image is Windows-only.
    echo.
    echo   Right-click the Docker Desktop tray icon -^> "Switch to Windows containers..."
    echo   Then run this script again.
    echo.
    goto :fail
)

if "%DOCKER_SERVER_OS%"=="" (
    echo [WARN] Could not read Docker server OS; continuing. If build fails, switch to Windows containers.
    echo.
)

if not exist "%CD%\artifacts" mkdir "%CD%\artifacts"

echo Running: docker compose -f Build\Docker\docker-compose.yml up --build --force-recreate
echo Output folder: %CD%\artifacts
echo.

docker compose version >nul 2>&1
if not errorlevel 1 (
    docker compose -f Build\Docker\docker-compose.yml up --build --force-recreate
) else (
    where docker-compose >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Neither "docker compose" nor "docker-compose" is available.
        goto :fail
    )
    docker-compose -f Build\Docker\docker-compose.yml up --build --force-recreate
)
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE% neq 0 (
    echo Docker finished with exit code %EXITCODE%.
    goto :end
)

echo ========================================
echo   BUILD SUCCESSFUL
echo ========================================
echo.
echo Output folder: %CD%\artifacts
echo.

REM Show summary from manifest.json if available
set "MANIFEST="
for /f "delims=" %%F in ('dir /s /b "%CD%\artifacts\*manifest.json" 2^>nul') do set "MANIFEST=%%F"
if defined MANIFEST (
    echo --- Artifact Manifest ---
    type "%MANIFEST%"
    echo.
    echo -------------------------
    echo.
) else (
    echo No manifest.json found in output.
    echo.
)

echo Artifacts:
dir /b /s "%CD%\artifacts\*" 2>nul | findstr /v manifest.json
echo.
goto :end

:fail
set EXITCODE=1

:end
echo.
pause
exit /b %EXITCODE%

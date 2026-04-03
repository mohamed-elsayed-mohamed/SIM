@echo off
REM Double-click to run the full pipeline on THIS PC (same as: python build.py).
REM For Docker instead, use RunDockerBuild.bat (Windows containers only).
REM With no arguments, settings come from build_config.json. To pass flags, run from cmd:
REM   RunBuild.bat --config Debug --version 1.2.3
REM Or create a shortcut and add arguments in the shortcut properties.

setlocal
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo Python was not found on PATH. Install Python 3.9+ and try again.
    pause
    exit /b 1
)

echo Running: python Build\Python\build.py %*
echo.
python Build\Python\build.py %*
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE% neq 0 (
    echo Build failed with exit code %EXITCODE%.
) else (
    echo Build finished successfully.
)
pause
exit /b %EXITCODE%

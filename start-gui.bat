@echo off
REM GCP VM Manager - Windows GUI Launcher
REM Double-click this file to launch the GUI application

echo.
echo =================================
echo   GCP VM Manager - GUI Launcher
echo =================================
echo Running from GitHub repository...
echo.

REM Configuration - Update this with your actual GitHub repo
set GITHUB_REPO=git+https://github.com/vanossj/gcp-vm-manager.git

REM Check if UV is installed
where uv >nul 2>&1
if errorlevel 1 (
    echo ERROR: UV package manager not found!
    echo.
    echo Please install UV first:
    echo 1. Run: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo 2. Restart this script
    echo.
    echo Or visit: https://docs.astral.sh/uv/getting-started/installation/
    echo.
    pause
    exit /b 1
)

echo ✓ UV package manager found
echo.

REM Launch the GUI application
echo Starting GCP VM Manager GUI...
echo Repository: %GITHUB_REPO%
echo.

uvx --from "%GITHUB_REPO%" gcp-vm-manager-gui

if errorlevel 1 (
    echo.
    echo ERROR: Failed to launch the application
    echo.
    echo Please check:
    echo - Internet connection is working
    echo - GitHub repository URL is correct
    echo - UV is properly installed
    echo.
    echo Repository: %GITHUB_REPO%
    echo.
) else (
    echo.
    echo Application completed successfully!
    echo.
)

pause

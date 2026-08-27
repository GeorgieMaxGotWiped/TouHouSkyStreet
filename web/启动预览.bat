@echo off
setlocal
cd /d "%~dp0"
echo Starting Touhou Sky Street website...
where python >nul 2>nul
if errorlevel 1 (
  py serve.py %1
) else (
  python serve.py %1
)
echo.
echo Server stopped. Close this window.
pause

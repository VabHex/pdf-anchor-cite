@echo off
REM PDF Anchor Cite launcher v1.0.0 (2026-11-24)
REM Double-click to start, or drag a summary .md file onto this file.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 serve.py %*
) else (
  python serve.py %*
)
if errorlevel 1 pause

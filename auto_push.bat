@echo off

REM Stage all changes
git add .

REM Get date in YYYY-MM-DD format (Windows 10 & 11 safe)
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set commit_date=%%I

REM Commit only if there are staged changes
git diff --cached --quiet || git commit -m "%commit_date%"

REM Push changes
git push

@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

set "REPO_URL=https://github.com/engamrhesham2002-cell/Rasd.git"
set "BRANCH=main"

echo ============================================
echo   Rasd - Push to GitHub
echo ============================================
echo.

where git >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Git is not installed or not in PATH.
  pause
  exit /b 1
)

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo [ERROR] This folder is not a Git repository.
  pause
  exit /b 1
)

git remote get-url origin >nul 2>&1
if errorlevel 1 (
  echo [SETUP] Adding GitHub remote...
  git remote add origin "%REPO_URL%"
)

echo [1/3] Contacting GitHub...
git fetch origin %BRANCH%
if errorlevel 1 (
  echo.
  echo [ERROR] Could not reach GitHub.
  echo Check your internet connection and your GitHub login.
  pause
  exit /b 1
)

echo.
echo [2/3] Saving local changes...
git add -A
git diff --cached --quiet
if not errorlevel 1 goto push

set "MSG="
set /p "MSG=Commit message (press Enter for automatic): "
if "!MSG!"=="" set "MSG=Update %DATE% %TIME%"
git commit -m "!MSG!"
if errorlevel 1 (
  echo [ERROR] Could not create the commit.
  pause
  exit /b 1
)

:push
echo.
echo [3/3] Uploading to GitHub...
git push -u origin HEAD:%BRANCH%
if not errorlevel 1 goto success

echo.
echo ============================================
echo   GitHub has different history
echo ============================================
echo The repository on GitHub was created separately from this local copy,
echo so a normal upload is rejected.
echo.
echo Safe option: I will first save the current GitHub branch as a backup
echo branch, then replace "%BRANCH%" with your local files.
echo.
choice /C YN /M "Do you want to continue"
if errorlevel 2 goto cancelled

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "STAMP=%%i"
echo.
echo Saving backup branch: backup-!STAMP!
git push origin FETCH_HEAD:refs/heads/backup-!STAMP!
if errorlevel 1 (
  echo [ERROR] Could not create the backup branch. Nothing was replaced.
  pause
  exit /b 1
)

echo Replacing %BRANCH% with local files...
git push --force-with-lease origin HEAD:%BRANCH%
if errorlevel 1 (
  echo.
  echo [ERROR] Upload failed. Your GitHub content was NOT changed.
  echo Make sure you are logged in to the correct GitHub account.
  pause
  exit /b 1
)

:success
echo.
echo ============================================
echo   DONE
echo ============================================
echo Repository: %REPO_URL%
echo Branch:     %BRANCH%
echo.
pause
exit /b 0

:cancelled
echo.
echo Cancelled. Nothing was uploaded.
echo Your local commit is saved and can be pushed later.
pause
exit /b 0

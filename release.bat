@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   Rasd - One-Click GitHub Release
echo ============================================

where powershell >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Windows PowerShell was not found.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0release.ps1" %*
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
  echo Release failed with code %RC%. Read the messages above.
  pause
  exit /b %RC%
)

echo All done.
pause
exit /b 0

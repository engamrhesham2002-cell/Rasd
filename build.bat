@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   Rasd - Build EXE
echo ============================================
echo.

echo [1/3] Installing build requirements...
py -3.11 -m pip install -r requirements-dev.txt
if errorlevel 1 goto fail

echo.
echo [2/3] Building (this may take a few minutes)...
py -3.11 -m PyInstaller Rasd.spec --noconfirm --clean
if errorlevel 1 goto fail

echo.
echo [3/3] Done.
echo.
echo EXE: dist\Rasd\Rasd.exe
echo IMPORTANT: copy the whole "dist\Rasd" folder, not only Rasd.exe.
echo.
pause
exit /b 0

:fail
echo.
echo Build failed. Check the messages above.
pause
exit /b 1

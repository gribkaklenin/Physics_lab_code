@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo Python was not found. Install Python and add it to PATH.
    exit /b 1
)

python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    python -m pip install --upgrade pyinstaller
    if errorlevel 1 exit /b 1
)

set "QT_EXCLUDE="
python -c "import PyQt6" >nul 2>&1
if not errorlevel 1 (
    set "QT_EXCLUDE=--exclude-module PyQt5"
) else (
    python -c "import PyQt5" >nul 2>&1
    if not errorlevel 1 (
        set "QT_EXCLUDE=--exclude-module PyQt6"
    ) else (
        echo PyQt6 or PyQt5 is required. Install one with: python -m pip install PyQt6
        exit /b 1
    )
)

echo Building AtwoodLab for Windows...
python -m PyInstaller --noconfirm --clean --onedir --windowed --noupx --name AtwoodLab --distpath "%~dp0dist" --workpath "%~dp0build" %QT_EXCLUDE% "%~dp0atwood_lab.py"
if errorlevel 1 (
    echo Build failed. The build log above contains the error.
    exit /b 1
)

echo.
echo Build complete: "%~dp0dist\AtwoodLab\AtwoodLab.exe"
echo Distribute the entire dist\AtwoodLab folder, not only the EXE.
exit /b 0

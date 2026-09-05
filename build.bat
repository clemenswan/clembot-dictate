@echo off
setlocal

echo ========================================
echo  Clembot-dictate -- Windows build
echo ========================================
echo.

:: Check PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo ERROR: PyInstaller not found.
    echo Run: pip install pyinstaller
    pause
    exit /b 1
)

:: Kill any running instance so PyInstaller can overwrite locked DLLs
taskkill /f /im "Clembot-dictate.exe" 2>nul
echo.

:: Generate icon
echo Generating icon...
python assets\make_icon.py
if errorlevel 1 (
    echo ERROR: Icon generation failed. Run: pip install pillow
    pause
    exit /b 1
)
echo.

:: Build
pyinstaller voice-transcriber.spec --clean
if errorlevel 1 (
    echo.
    echo BUILD FAILED. Check errors above.
    pause
    exit /b 1
)

:: Compile Inno Setup installer (requires Inno Setup 6)
set ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if exist "%ISCC%" (
    echo.
    echo Compiling installer...
    "%ISCC%" installer.iss
    if errorlevel 1 (
        echo WARNING: Installer compilation failed. EXE is still in dist\Clembot-dictate\
    ) else (
        echo Installer: dist\Clembot-dictate-Setup-1.3.0.exe
    )
) else (
    echo.
    echo NOTE: Inno Setup 6 not found -- skipping installer.
    echo       Install from: https://jrsoftware.org/isinfo.php
    echo       Then re-run build.bat to generate the installer EXE.
)

echo.
echo ========================================
echo  Build complete.
echo  EXE:       dist\Clembot-dictate\Clembot-dictate.exe
echo  Installer: dist\Clembot-dictate-Setup-1.3.0.exe (if Inno Setup installed)
echo.
echo  First-run note:
echo  The faster-whisper model (~74 MB) will download
echo  automatically on first launch if not already cached.
echo  Cache location: %%USERPROFILE%%\.cache\huggingface\hub\
echo ========================================
pause

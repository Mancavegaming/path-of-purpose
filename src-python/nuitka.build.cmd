@echo off
REM Path of Purpose — Nuitka build script for Windows
REM Requires: pip install nuitka ordered-set zstandard
REM Requires: MSVC (Visual Studio Build Tools) or MinGW

python -m nuitka ^
    --onefile ^
    --output-dir=build ^
    --include-package=pop ^
    --include-data-dir=pop/knowledge/cache=pop/knowledge/cache ^
    --include-data-dir=pop/gamedata/cache=pop/gamedata/cache ^
    --include-data-dir=pop/ai/skill_profiles=pop/ai/skill_profiles ^
    --enable-plugin=anti-bloat ^
    --assume-yes-for-downloads ^
    --windows-console-mode=disable ^
    --company-name="Path of Purpose" ^
    --product-name="Path of Purpose Engine" ^
    --file-version=0.1.0 ^
    --product-version=0.1.0 ^
    pop\main.py

echo.
echo Build complete. Output: build\main.exe
echo Copy to Tauri: copy build\main.exe ..\src-tauri-app\src-tauri\binaries\pop-engine-x86_64-pc-windows-msvc.exe
pause

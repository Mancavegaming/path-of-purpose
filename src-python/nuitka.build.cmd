@echo off
REM Path of Purpose — Nuitka build script for Windows
REM Requires: pip install nuitka ordered-set zstandard
REM Requires: MSVC (Visual Studio Build Tools) or MinGW

python -m nuitka ^
    --standalone ^
    --output-dir=build ^
    --include-package=pop ^
    --enable-plugin=anti-bloat ^
    --windows-console-mode=disable ^
    --company-name="Path of Purpose" ^
    --product-name="Path of Purpose Engine" ^
    --file-version=0.1.0 ^
    --product-version=0.1.0 ^
    pop\main.py

echo.
echo Build complete. Output in build\main.dist\
pause

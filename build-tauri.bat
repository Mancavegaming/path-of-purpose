@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >NUL 2>&1
cd /d "D:\Dev\Path of Purpose\src-tauri-app\src-tauri"
set PATH=%USERPROFILE%\.cargo\bin;%PATH%
cargo check > "D:\Dev\Path of Purpose\build-output.txt" 2>&1
echo %ERRORLEVEL% > "D:\Dev\Path of Purpose\build-exitcode.txt"

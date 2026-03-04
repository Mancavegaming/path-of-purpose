$vsPath = "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
$projectDir = "D:\Dev\Path of Purpose\src-tauri-app\src-tauri"
$cargoPath = "$env:USERPROFILE\.cargo\bin"

cmd /c "`"$vsPath`" >NUL 2>&1 && set PATH=$cargoPath;%PATH% && cd /d `"$projectDir`" && cargo check" 2>&1

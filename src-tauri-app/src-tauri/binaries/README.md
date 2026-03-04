Place the Python sidecar binary here.

Tauri expects the binary named with a target-triple suffix:
  pop-engine-x86_64-pc-windows-msvc.exe

To build it from the Python project:
  cd ../../src-python
  python -m nuitka --standalone --output-dir=build pop/main.py
  copy build/main.dist/main.exe ../src-tauri-app/src-tauri/binaries/pop-engine-x86_64-pc-windows-msvc.exe

During development, you can also create a wrapper .bat script.

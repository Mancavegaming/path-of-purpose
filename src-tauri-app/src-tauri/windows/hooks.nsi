; Path of Purpose — NSIS installer hooks
; Adds/removes Windows Defender exclusions so the Nuitka sidecar
; doesn't trigger high CPU from Antimalware Service Executable.

!macro NSIS_HOOK_POSTINSTALL
  ; Add Defender exclusion for the install directory (covers main exe + sidecar)
  nsExec::ExecToStack 'powershell -inputformat none -ExecutionPolicy Bypass -Command "\
    try { \
      Add-MpPreference -ExclusionPath \"$INSTDIR\" -ErrorAction SilentlyContinue; \
      Add-MpPreference -ExclusionProcess \"$INSTDIR\Path of Purpose.exe\" -ErrorAction SilentlyContinue; \
      Add-MpPreference -ExclusionProcess \"$INSTDIR\pop-engine-x86_64-pc-windows-msvc.exe\" -ErrorAction SilentlyContinue; \
    } catch {} \
  "'
  Pop $0
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  ; Remove Defender exclusions on uninstall to keep the system clean
  nsExec::ExecToStack 'powershell -inputformat none -ExecutionPolicy Bypass -Command "\
    try { \
      Remove-MpPreference -ExclusionPath \"$INSTDIR\" -ErrorAction SilentlyContinue; \
      Remove-MpPreference -ExclusionProcess \"$INSTDIR\Path of Purpose.exe\" -ErrorAction SilentlyContinue; \
      Remove-MpPreference -ExclusionProcess \"$INSTDIR\pop-engine-x86_64-pc-windows-msvc.exe\" -ErrorAction SilentlyContinue; \
    } catch {} \
  "'
  Pop $0
!macroend

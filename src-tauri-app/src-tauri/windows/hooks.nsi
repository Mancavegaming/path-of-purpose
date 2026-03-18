; Path of Purpose — NSIS installer hooks
; Adds/removes Windows Defender exclusions so the Nuitka sidecar
; doesn't trigger high CPU from Antimalware Service Executable.
;
; The sidecar (pop-engine.exe) is Nuitka-compiled and triggers ML-based
; false positives (Bearfoos.B!ml, Wacatac.B!ml, Contebrew.A!ml).
; We exclude by path, process name, and the AppData directory.

!macro NSIS_HOOK_POSTINSTALL
  ; Exclude the install directory (covers all binaries)
  nsExec::ExecToStack 'powershell -inputformat none -ExecutionPolicy Bypass -Command "\
    try { \
      Add-MpPreference -ExclusionPath \"$INSTDIR\" -ErrorAction SilentlyContinue; \
      Add-MpPreference -ExclusionPath \"$LOCALAPPDATA\com.pathofpurpose.app\" -ErrorAction SilentlyContinue; \
      Add-MpPreference -ExclusionProcess \"path-of-purpose.exe\" -ErrorAction SilentlyContinue; \
      Add-MpPreference -ExclusionProcess \"pop-engine.exe\" -ErrorAction SilentlyContinue; \
    } catch {} \
  "'
  Pop $0
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  ; Clean up all exclusions
  nsExec::ExecToStack 'powershell -inputformat none -ExecutionPolicy Bypass -Command "\
    try { \
      Remove-MpPreference -ExclusionPath \"$INSTDIR\" -ErrorAction SilentlyContinue; \
      Remove-MpPreference -ExclusionPath \"$LOCALAPPDATA\com.pathofpurpose.app\" -ErrorAction SilentlyContinue; \
      Remove-MpPreference -ExclusionProcess \"path-of-purpose.exe\" -ErrorAction SilentlyContinue; \
      Remove-MpPreference -ExclusionProcess \"pop-engine.exe\" -ErrorAction SilentlyContinue; \
    } catch {} \
  "'
  Pop $0
!macroend

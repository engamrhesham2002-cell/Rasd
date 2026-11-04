; ===========================================================================
;  Rasd installer (standard from v0.42)
;
;  Designed around the app's own updater (updates.py / update_utils.py):
;   - The updater downloads the first *.exe asset of the latest GitHub release
;     and runs it as:  RasdSetup.exe /SILENT /NORESTART
;     (NSIS only knows /S, so /SILENT is mapped to silent mode in .onInit)
;   - After the installer exits, the updater relaunches the exe from the OLD
;     install path, so upgrades must always land in the same folder.
;   - All user data lives in %LOCALAPPDATA%\Rasd, never in the install folder.
;   - Per-user install (no admin) => updates never show a UAC prompt and also
;     work for standard (non-admin) Windows accounts.
;
;  Build:  makensis /DAPP_VERSION=0.43 /DROOT="<project folder>" build_installer.nsi
;          (release.ps1 does this automatically)
; ===========================================================================
Unicode true

!include "MUI2.nsh"
!include "FileFunc.nsh"

!ifndef ROOT
  !define ROOT "."
!endif
!ifndef APP_VERSION
  !define APP_VERSION "0.43"
!endif

!define APP_NAME      "Rasd Project Manager"
!define APP_PUBLISHER "ENG. Amr Hesham"
!define APP_EXE       "Rasd.exe"
!define APP_URL       "https://github.com/engamrhesham2002-cell/Rasd"
!define UNINST_KEY    "Software\Microsoft\Windows\CurrentVersion\Uninstall\Rasd"

Name "${APP_NAME}"
OutFile "${ROOT}\release\RasdSetup.exe"
InstallDir "$LOCALAPPDATA\Programs\Rasd"
InstallDirRegKey HKCU "${UNINST_KEY}" "InstallLocation"
RequestExecutionLevel user
SetCompressor /SOLID lzma

VIProductVersion "${APP_VERSION}.0.0"
VIAddVersionKey "ProductName"      "${APP_NAME}"
VIAddVersionKey "CompanyName"      "${APP_PUBLISHER}"
VIAddVersionKey "FileDescription"  "${APP_NAME} Installer"
VIAddVersionKey "FileVersion"      "${APP_VERSION}"
VIAddVersionKey "ProductVersion"   "${APP_VERSION}"
VIAddVersionKey "LegalCopyright"   "Copyright (c) 2026 ${APP_PUBLISHER}"

; ---------- UI ----------
!define MUI_ICON   "${ROOT}\Assets\rasd_logo.ico"
!define MUI_UNICON "${ROOT}\Assets\rasd_logo.ico"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch Rasd"

!insertmacro MUI_PAGE_WELCOME
!define MUI_PAGE_CUSTOMFUNCTION_LEAVE DirLeave
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "Arabic"
!insertmacro MUI_LANGUAGE "English"

; ---------- Functions ----------
Function .onInit
  ; The in-app updater calls: RasdSetup.exe /SILENT /NORESTART
  ${GetParameters} $R0
  ClearErrors
  ${GetOptions} $R0 "/SILENT" $R1
  IfErrors +2 0
    SetSilent silent
  ClearErrors
  ${GetOptions} $R0 "/VERYSILENT" $R1
  IfErrors +2 0
    SetSilent silent

  ; Notice for machines that still have an old all-users (Program Files) install
  IfSilent done_legacy
  ReadRegStr $R2 HKLM "${UNINST_KEY}" "UninstallString"
  StrCmp $R2 "" 0 legacy_found
  SetRegView 64
  ReadRegStr $R2 HKLM "${UNINST_KEY}" "UninstallString"
  SetRegView 32
  StrCmp $R2 "" done_legacy
  legacy_found:
    MessageBox MB_OK|MB_ICONINFORMATION "An older all-users installation of Rasd was found.$\r$\nPlease uninstall it from Windows Settings > Apps after this installation finishes, to avoid having two copies."
  done_legacy:
FunctionEnd

; Always install into a folder named "Rasd" so the uninstaller can never
; wipe a folder such as C:\ or Documents.
Function DirLeave
  StrCpy $0 $INSTDIR "" -5
  StrCmp $0 "\Rasd" +2 0
    StrCpy $INSTDIR "$INSTDIR\Rasd"
FunctionEnd

Function un.onInit
  StrCpy $0 $INSTDIR "" -5
  StrCmp $0 "\Rasd" +3 0
    MessageBox MB_OK|MB_ICONSTOP "Unexpected uninstall location. Aborting for safety."
    Abort
FunctionEnd

; ---------- Install ----------
Section "MainSection" SEC01
  SetShellVarContext current

  ; Make sure a running copy does not block file replacement
  nsExec::Exec 'taskkill /F /IM ${APP_EXE}'
  Sleep 800

  SetOutPath "$INSTDIR"
  ; Whole PyInstaller output folder (Rasd.exe + _internal)
  File /r "${ROOT}\dist\Rasd\*"

  WriteUninstaller "$INSTDIR\uninstall.exe"

  CreateShortcut "$DESKTOP\Rasd.lnk" "$INSTDIR\${APP_EXE}"
  CreateDirectory "$SMPROGRAMS\Rasd"
  CreateShortcut "$SMPROGRAMS\Rasd\Rasd.lnk" "$INSTDIR\${APP_EXE}"
  CreateShortcut "$SMPROGRAMS\Rasd\Uninstall.lnk" "$INSTDIR\uninstall.exe"

  ; Apps & Features entry (per-user)
  WriteRegStr   HKCU "${UNINST_KEY}" "DisplayName"     "${APP_NAME}"
  WriteRegStr   HKCU "${UNINST_KEY}" "DisplayVersion"  "${APP_VERSION}"
  WriteRegStr   HKCU "${UNINST_KEY}" "DisplayIcon"     "$INSTDIR\${APP_EXE}"
  WriteRegStr   HKCU "${UNINST_KEY}" "UninstallString" "$INSTDIR\uninstall.exe"
  WriteRegStr   HKCU "${UNINST_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr   HKCU "${UNINST_KEY}" "Publisher"       "${APP_PUBLISHER}"
  WriteRegStr   HKCU "${UNINST_KEY}" "URLInfoAbout"    "${APP_URL}"
  WriteRegDWORD HKCU "${UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINST_KEY}" "NoRepair" 1
SectionEnd

; ---------- Uninstall ----------
Section "Uninstall"
  SetShellVarContext current

  nsExec::Exec 'taskkill /F /IM ${APP_EXE}'
  Sleep 800

  ; Program files only. Projects/settings in %LOCALAPPDATA%\Rasd are kept.
  RMDir /r "$INSTDIR"

  Delete "$DESKTOP\Rasd.lnk"
  Delete "$SMPROGRAMS\Rasd\Rasd.lnk"
  Delete "$SMPROGRAMS\Rasd\Uninstall.lnk"
  RMDir  "$SMPROGRAMS\Rasd"

  ; Downloaded update installers are disposable
  RMDir /r "$LOCALAPPDATA\Rasd\updates"

  DeleteRegKey HKCU "${UNINST_KEY}"
SectionEnd

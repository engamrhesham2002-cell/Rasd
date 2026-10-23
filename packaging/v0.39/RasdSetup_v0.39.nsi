Unicode true
!include "MUI2.nsh"

!define APP_NAME "Rasd"
!define APP_VERSION "0.39"
!define APP_PUBLISHER "ENG.Amr Hesham"
!define APP_UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\Rasd"
!define RELEASE_ROOT "${__FILEDIR__}\..\..\source\v0.39"

Name "${APP_NAME} ${APP_VERSION}"
Caption "Install ${APP_NAME} ${APP_VERSION}"
OutFile "D:\rasd\0.39 installers\Installers\Standard\RasdSetup_v0.39.exe"
InstallDir "$LOCALAPPDATA\Programs\Rasd"
RequestExecutionLevel user
SetCompressor /SOLID lzma
Icon "${RELEASE_ROOT}\Assets\product.ico"
UninstallIcon "${RELEASE_ROOT}\Assets\product.ico"

!define MUI_ABORTWARNING
!define MUI_ICON "${RELEASE_ROOT}\Assets\product.ico"
!define MUI_UNICON "${RELEASE_ROOT}\Assets\product.ico"
!define MUI_FINISHPAGE_RUN "$INSTDIR\Rasd.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch Rasd"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Function .onInit
  SetShellVarContext current
FunctionEnd

Section "Install Rasd" SEC_MAIN
  SetShellVarContext current
  SetOutPath "$INSTDIR"
  File "${RELEASE_ROOT}\Rasd.exe"
  FileOpen $0 "$INSTDIR\.rasd-installed" w
  FileWrite $0 "Rasd ${APP_VERSION}\r\n"
  FileClose $0
  CreateDirectory "$INSTDIR\Log"
  SetOutPath "$INSTDIR\Python Source"
  File "${RELEASE_ROOT}\core.py"
  File "${RELEASE_ROOT}\main_ui.py"
  File "${RELEASE_ROOT}\files.py"
  File "${RELEASE_ROOT}\search.py"
  File "${RELEASE_ROOT}\previews.py"
  File "${RELEASE_ROOT}\build_single.py"
  File "${RELEASE_ROOT}\split_modules.py"
  File "${RELEASE_ROOT}\Rasd_v0.39.spec"
  File "${RELEASE_ROOT}\README_SOURCE.txt"
  File "${RELEASE_ROOT}\requirements-build.txt"
  File "${RELEASE_ROOT}\LICENSE"
  File "${RELEASE_ROOT}\THIRD_PARTY_NOTICES.md"
  SetOutPath "$INSTDIR\Python Source\full code"
  File "${RELEASE_ROOT}\full code\app.py"
  SetOutPath "$INSTDIR\Python Source\Assets"
  File "${RELEASE_ROOT}\Assets\welcome_art.jpg"
  File "${RELEASE_ROOT}\Assets\rasd_logo.png"
  File "${RELEASE_ROOT}\Assets\rasd_wordmark.png"
  File "${RELEASE_ROOT}\Assets\product.ico"
  File "${RELEASE_ROOT}\Assets\Everything-License.txt"
  SetOutPath "$INSTDIR\Python Source\Everything"
  File "${RELEASE_ROOT}\Everything\Everything.exe"
  File "${RELEASE_ROOT}\Everything\es.exe"
  File "${RELEASE_ROOT}\Everything\Everything.lng"
  File "${RELEASE_ROOT}\Everything\License.txt"
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  CreateDirectory "$SMPROGRAMS\Rasd"
  CreateShortcut "$SMPROGRAMS\Rasd\Rasd.lnk" "$INSTDIR\Rasd.exe" "" "$INSTDIR\Rasd.exe" 0
  CreateShortcut "$SMPROGRAMS\Rasd\Uninstall Rasd.lnk" "$INSTDIR\Uninstall.exe"
  CreateShortcut "$DESKTOP\Rasd.lnk" "$INSTDIR\Rasd.exe" "" "$INSTDIR\Rasd.exe" 0

  WriteRegStr HKCU "${APP_UNINSTALL_KEY}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "${APP_UNINSTALL_KEY}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "${APP_UNINSTALL_KEY}" "Publisher" "${APP_PUBLISHER}"
  WriteRegStr HKCU "${APP_UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${APP_UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\Rasd.exe"
  WriteRegStr HKCU "${APP_UNINSTALL_KEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
SectionEnd

Section "Uninstall"
  SetShellVarContext current
  Delete "$SMPROGRAMS\Rasd\Rasd.lnk"
  Delete "$SMPROGRAMS\Rasd\Uninstall Rasd.lnk"
  RMDir "$SMPROGRAMS\Rasd"
  Delete "$DESKTOP\Rasd.lnk"
  DeleteRegKey HKCU "${APP_UNINSTALL_KEY}"
  Delete "$INSTDIR\.rasd-installed"
  Delete "$INSTDIR\Rasd.exe"
  Delete "$INSTDIR\Uninstall.exe"
  Delete "$INSTDIR\Python Source\core.py"
  Delete "$INSTDIR\Python Source\main_ui.py"
  Delete "$INSTDIR\Python Source\files.py"
  Delete "$INSTDIR\Python Source\search.py"
  Delete "$INSTDIR\Python Source\previews.py"
  Delete "$INSTDIR\Python Source\build_single.py"
  Delete "$INSTDIR\Python Source\split_modules.py"
  Delete "$INSTDIR\Python Source\Rasd_v0.39.spec"
  Delete "$INSTDIR\Python Source\README_SOURCE.txt"
  Delete "$INSTDIR\Python Source\requirements-build.txt"
  Delete "$INSTDIR\Python Source\LICENSE"
  Delete "$INSTDIR\Python Source\THIRD_PARTY_NOTICES.md"
  Delete "$INSTDIR\Python Source\full code\app.py"
  Delete "$INSTDIR\Python Source\Assets\welcome_art.jpg"
  Delete "$INSTDIR\Python Source\Assets\rasd_logo.png"
  Delete "$INSTDIR\Python Source\Assets\rasd_wordmark.png"
  Delete "$INSTDIR\Python Source\Assets\product.ico"
  Delete "$INSTDIR\Python Source\Assets\Everything-License.txt"
  Delete "$INSTDIR\Python Source\Everything\Everything.exe"
  Delete "$INSTDIR\Python Source\Everything\es.exe"
  Delete "$INSTDIR\Python Source\Everything\Everything.lng"
  Delete "$INSTDIR\Python Source\Everything\License.txt"
  RMDir "$INSTDIR\Python Source\full code"
  RMDir "$INSTDIR\Python Source\Assets"
  RMDir "$INSTDIR\Python Source\Everything"
  RMDir "$INSTDIR\Python Source"
  RMDir "$INSTDIR\Log"
  RMDir "$INSTDIR"
SectionEnd



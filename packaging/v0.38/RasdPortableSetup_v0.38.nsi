Unicode true
!include "MUI2.nsh"

!define APP_NAME "Rasd Portable"
!define APP_VERSION "0.38"
!define RELEASE_ROOT "${__FILEDIR__}\..\..\source\v0.38"

Name "${APP_NAME} ${APP_VERSION}"
Caption "Install ${APP_NAME} ${APP_VERSION}"
OutFile "${__FILEDIR__}\RasdPortableSetup_v0.38.exe"
InstallDir "$EXEDIR\Rasd_v0.38_Portable"
RequestExecutionLevel user
SetCompressor /SOLID lzma
Icon "${RELEASE_ROOT}\Assets\product.ico"

!define MUI_ABORTWARNING
!define MUI_ICON "${RELEASE_ROOT}\Assets\product.ico"
!define MUI_FINISHPAGE_RUN "$INSTDIR\Rasd.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch Rasd Portable"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "English"

Function .onInit
  SetShellVarContext current
FunctionEnd

Section "Install portable folder" SEC_MAIN
  SetOutPath "$INSTDIR"
  File "${RELEASE_ROOT}\Rasd.exe"
  FileOpen $0 "$INSTDIR\.rasd-portable" w
  FileWrite $0 "Rasd Portable ${APP_VERSION}\r\n"
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
  File "${RELEASE_ROOT}\Rasd_v0.38.spec"
  File "${RELEASE_ROOT}\README_SOURCE.txt"
  File "${RELEASE_ROOT}\requirements-build.txt"
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
  FileOpen $0 "$INSTDIR\HOW_TO_MOVE.txt" w
  FileWrite $0 "Close Rasd, then move the complete Rasd_v0.38_Portable folder. Keep Rasd.exe and Log together.\r\n"
  FileClose $0
SectionEnd


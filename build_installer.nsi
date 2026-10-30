!include "MUI2.nsh"

Name "Rasd Project Manager"
OutFile "RasdSetup.exe"
InstallDir "$PROGRAMFILES\Rasd"
RequestExecutionLevel admin

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; صفحة إلغاء التثبيت
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "Arabic"
!insertmacro MUI_LANGUAGE "English"

Section "MainSection" SEC01
  SetOutPath "$INSTDIR"
  
  ; نسخ كافة محتويات فولدر البرنامج المجمع من PyInstaller
  File /r "dist\Rasd\*"
  
  ; إنشاء اختصار على سطح المكتب
  CreateShortcut "$DESKTOP\Rasd.lnk" "$INSTDIR\Rasd.exe"
  
  ; إنشاء مجلد واختصارات في قائمة ابدأ
  CreateDirectory "$SMPROGRAMS\Rasd"
  CreateShortcut "$SMPROGRAMS\Rasd\Rasd.lnk" "$INSTDIR\Rasd.exe"
  CreateShortcut "$SMPROGRAMS\Rasd\Uninstall.lnk" "$INSTDIR\uninstall.exe"

  ; كتابة مفاتيح التسجيل لكي يظهر البرنامج في لوحة التحكم (Control Panel)
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Rasd" "DisplayName" "Rasd Project Manager"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Rasd" "DisplayIcon" "$INSTDIR\Rasd.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Rasd" "UninstallString" "$INSTDIR\uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Rasd" "Publisher" "ENG. Amr Hesham"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Rasd" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Rasd" "NoRepair" 1

  ; إنشاء ملف إلغاء التثبيت
  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "Uninstall"
  ; حذف ملفات البرنامج
  RMDir /r "$INSTDIR"
  
  ; حذف الاختصارات
  Delete "$DESKTOP\Rasd.lnk"
  Delete "$SMPROGRAMS\Rasd\Rasd.lnk"
  Delete "$SMPROGRAMS\Rasd\Uninstall.lnk"
  RMDir "$SMPROGRAMS\Rasd"

  ; مسح مفاتيح التسجيل من لوحة التحكم
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Rasd"
SectionEnd
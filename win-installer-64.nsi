;NSIS Modern User Interface
;Start Menu Folder Selection Example Script
;Written by Joost Verburg

;Include Modern UI

  !include "MUI2.nsh"
  !include x64.nsh

  ; Best Compression
  SetCompress Auto
  SetCompressor /SOLID lzma
  SetCompressorDictSize 32
  SetDatablockOptimize On

;General

  ;Name and file
  Name "CecogAnalyzer-${mver}"
  OutFile "CecogAnalyzer-setup.exe"

  ;Default installation folder
  InstallDir "$PROGRAMFILES64\CecogAnalyzer-${mver}"

  ;Get installation folder from registry if available
  InstallDirRegKey HKCU "Software\CecogAnalyzer-${mver}" ""

  ;Request application privileges for Windows Vista
  ;RequestExecutionLevel admin

  ; MultiUser.nsh will set the RequestExecutionLevel flag to request privileges.
    !define MULTIUSER_EXECUTIONLEVEL Highest
    !define MULTIUSER_MUI
    ;!define MULTIUSER_NOUNINSTALL ;Uncomment if no uninstaller is created
    !include MultiUser.nsh
    !include MUI2.nsh

    Function .onInit
      !insertmacro MULTIUSER_INIT
    FunctionEnd

    Function un.onInit
      !insertmacro MULTIUSER_UNINIT
    FunctionEnd

;Variables
  Var StartMenuFolder

;Interface Settings
  !define MUI_ABORTWARNING

;Pages
  !insertmacro MULTIUSER_PAGE_INSTALLMODE
  !insertmacro MUI_PAGE_COMPONENTS
  !insertmacro MUI_PAGE_DIRECTORY

  ;Start Menu Folder Page Configuration
  !define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKCU"
  !define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\CecogAnalyzer-${mver}"
  !define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "Start Menu Folder"

  !insertmacro MUI_PAGE_STARTMENU Application $StartMenuFolder

  !insertmacro MUI_PAGE_INSTFILES

  !insertmacro MUI_UNPAGE_CONFIRM
  !insertmacro MUI_UNPAGE_INSTFILES
  !define MUI_FINISHPAGE_NOAUTOCLOSE
    !define MUI_FINISHPAGE_RUN
    !define MUI_FINISHPAGE_RUN_NOTCHECKED
    !define MUI_FINISHPAGE_RUN_TEXT "Start CecogAnalyzer"
    !define MUI_FINISHPAGE_RUN_FUNCTION "LaunchLink"
    ;!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED
    ;!define MUI_FINISHPAGE_SHOWREADME $INSTDIR\readme.txt
  !insertmacro MUI_PAGE_FINISH

;Languages
  !insertmacro MUI_LANGUAGE "English"

 Function LaunchLink
  SetShellVarContext all
  ;MessageBox MB_OK "Reached LaunchLink $\r$\n \
                   ;SMPROGRAMS: $SMPROGRAMS  $\r$\n \
                   ;Start Menu Folder: $STARTMENU_FOLDER $\r$\n \
                   ;InstallDirectory: $INSTDIR "
  ExecShell "" "$SMPROGRAMS\$StartMenuFolder\CecogAnalyzer-${mver}.lnk"
FunctionEnd

;Installer Sections
Section "CecogAnalyzer" SecDummy

  SectionIn RO
  SetOutPath "$INSTDIR"
  SetShellVarContext all
  RMDir /r "$%APPDATA%\CellCognition${mver}"

  File /r dist\*.*

  ;Store installation folder
  WriteRegStr HKCU "Software\CecogAnalyzer-${mver}" "" $INSTDIR

  ;Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  !insertmacro MUI_STARTMENU_WRITE_BEGIN Application

    ;Create shortcutsdist\resources\battery_package\settings\demo_settings.conf
    SetShellVarContext all
    CreateDirectory "$SMPROGRAMS\$StartMenuFolder"

    CreateShortCut "$SMPROGRAMS\$StartMenuFolder\CecogAnalyzer-${mver}.lnk" "$INSTDIR\CecogAnalyzer.exe" "" "$INSTDIR\CecogAnalyzer.exe"
    CreateShortCut "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk" "$INSTDIR\Uninstall.exe"

  AccessControl::GrantOnFile "$INSTDIR" "(S-1-5-32-545)" "FullAccess"

  !insertmacro MUI_STARTMENU_WRITE_END

SectionEnd

Section /o "Battery package" SecDemo
  SetOutPath "$INSTDIR\resources\battery_package"
  FILE /r dist\resources\battery_package\*.*
SectionEnd

;Descriptions

  ;Language strings
  LangString DESC_SecDummy ${LANG_ENGLISH} "CecogAnalyzer binaries (required)"

  ;Assign language strings to sections
  !insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecDummy} $(DESC_SecDummy)
    ; !insertmacro MUI_DESCRIPTION_TEXT ${SecDemo} "Battery package - Demo data"
  !insertmacro MUI_FUNCTION_DESCRIPTION_END

;Uninstaller Section

Section "Uninstall"
  ;ADD YOUR OWN FILES HERE...

  Delete "$INSTDIR\Uninstall.exe"

  RMDir /r "$INSTDIR"
  SetShellVarContext all
  RMDir /r "$%APPDATA%\CellCognition${mver}"

  !insertmacro MUI_STARTMENU_GETFOLDER Application $StartMenuFolder

  Delete "$SMPROGRAMS\$StartMenuFolder\CecogAnalyzer-${mver}.lnk"
  Delete "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk"
  RMDir /r "$SMPROGRAMS\$StartMenuFolder"

  DeleteRegKey /ifempty HKCU "Software\CecogAnalyzer-${mver}"

SectionEnd

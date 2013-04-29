@SETLOCAL
:: this line is one uses windows sdk build environment
echo using Windows SDK's environment for x64 build
set VS90COMNTOOLS=%VS100COMNTOOLS%
@Set /P _clean=Clean directories manually? [Y/n] || Set _clean="n"

@If "%_clean%"=="Y" goto:clean
@If "%_clean%"=="y" goto:clean
goto:build

::should be replaced by a separate python setup.py clean command
:clean
rmdir /Q /S dist
rmdir /Q /S build
erase /Q *.exe

:build
python setup_windows.py py2exe

@Set /P _nsis=Build NSIS-installer [Y/n] || Set _nsis="n"
@If "%_nsis%"=="Y" goto:nsis
@If "%_nsis%"=="y" goto:nsis
@goto:eof

:nsis
CALL git describe --tags > build.info
for /F "delims=\" %%a in (build.info) do (
	set temp=%%a
)
SET mver="1.4.0"
pause

makensis /Dmver=%mver% win-installer-64.nsi
rename CecogAnalyzer-setup.exe CecogAnalyzer_%temp%_x86_64.exe
@ENDLOCAL

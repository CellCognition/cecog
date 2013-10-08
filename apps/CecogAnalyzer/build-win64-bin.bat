@SETLOCAL
@set CECOGPATH=Z:\workbench\cecog
@set PYTHONPATH=%PYTHONPATH%;%CECOGPATH%\pysrc

@set PATH=%PATH%;C:\Python27\Lib\site-packages\numpy
@set PATH=%PATH%;C:\Python27\Lib\site-packages\numpy\core

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
SET mver="1.4.1"
pause

makensis /Dmver=%mver% build-win-installer-64.nsi
rename CecogAnalyzer-setup.exe CecogAnalyzer_%temp%_x86_64.exe
@ENDLOCAL

@SETLOCAL

:: this line is one uses windows sdk build environment
@IF NOT "%VS110COMNTOOLS%"=="" set VS90COMNTOOLS=%VS110COMNTOOLS%
@IF NOT "%VS120COMNTOOLS%"=="" set VS90COMNTOOLS=%VS120COMNTOOLS%

@Set /P _clean=Clean directories manually? [Y/n] || Set _clean="n"

@If "%_clean%"=="Y" goto:clean
@If "%_clean%"=="y" goto:clean
goto:build

::should be replaced by a separate python setup.py clean command
:clean
rmdir /Q /S dist
rmdir /Q /S build
erase /Q *.exe
erase pysrc\cecog\ccore\_cecog.pyd

:build
python setup_windows.py py2exe

@Set /P _nsis=Build NSIS-installer [Y/n] || Set _nsis="n"
@If "%_nsis%"=="Y" goto:nsis
@If "%_nsis%"=="y" goto:nsis
@goto:eof

:nsis
SET VERSION="1.5.3"
pause

makensis /Dmver=%VERSION% win-installer-64.nsi
rename CecogAnalyzer-setup.exe CecogAnalyzer_%VERSION%_x86_64.exe
@ENDLOCAL

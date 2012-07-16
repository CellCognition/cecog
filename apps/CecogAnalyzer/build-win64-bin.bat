set PYTHONPATH=C:\Users\sommerc\cellcognition\pysrc
set PATH=%PATH%;C:\Python27\Lib\site-packages\numpy

python setup.py py2exe

copy /Y jpeg62.dll .\dist\
copy /Y QtCore4.dll .\dist\
copy /Y QtGui4.dll .\dist\
copy /Y C:\depend64\bin\hdf5_hldll.dll .\dist\
copy /Y C:\depend64\bin\hdf5dll.dll .\dist\

copy /Y C:\depend64\bin\zlib1.dll .\dist\
copy /Y C:\depend64\bin\szip.dll .\dist\

CALL git describe --tags > build.info
for /F "delims=\" %%a in (build.info) do (
	set temp=%%a
)
SET mver="1.2.5"
pause

makensis /Dmver=%mver% build-win-installer-64.nsi

rename CecogAnalyzer-setup.exe CecogAnalyzer_%temp%_Windows_64bit.exe


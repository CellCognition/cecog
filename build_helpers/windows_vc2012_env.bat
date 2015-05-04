:: set path variable accordingly, vs90comntools needs to be set manually
set "PATH=%PATH%;c:\Program Files (x86)\Microsoft Visual Studio 11.0\VC\"
vcvarsall.bat amd64
echo "run the following command"
echo "SET VS90COMNTOOLS=%VS110COMNTOOLS%"

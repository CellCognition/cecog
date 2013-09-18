:: little helper to set up Windows SDK's build environment
:: certain windows setups do not find the compiler directory
set PATH=%PATH%;C:\Program Files (x86)\Microsoft Visual Studio 10.0\VC\bin\x86_amd64
set DISTUTILS_USE_SDK=1
set MSSdk=1
"C:\Program Files\Microsoft SDKs\Windows\v7.1\Bin\SetEnv.Cmd" /x64 /Release


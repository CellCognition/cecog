#!/bin/sh

version=$1
volname="CecogAnalyzer-"$version
dmgfile="CecogAnalyzer_"$version"_MacOSX_Intel64.dmg"
tmp="temp.sparseimage"
appname="CecogAnalyzer-"$version".app"

echo $version
echo $volname
echo $appname 
echo $dmgfile

cp CecogAnalyzer_template.sparseimage $tmp
hdiutil resize -size 90m $tmp
hdiutil attach $tmp
diskutil rename /Volumes/CecogAnalyzer $volname

#mv dist/CecogAnalyzer.app /Volumes/$volname
rm -rf /Volumes/$volname/CecogAnalyzer.app
cp -RHp dist/CecogAnalyzer.app /Volumes/$volname/
#mv /Volumes/$volname/CecogAnalyzer.app /Volumes/$volname/$appname

# lock the folder: disable any modification on the icons etc. 
# (see small icon in upper left corner)
#/Developer/Tools/SetFile -a L /Volumes/$volname

hdiutil eject /Volumes/$volname
hdiutil convert $tmp -ov -format UDBZ -o $dmgfile
rm $tmp
open $dmgfile
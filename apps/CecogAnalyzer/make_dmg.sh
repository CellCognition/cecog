#!/bin/sh
# MH 2011/07
#
# HOWTO create DMG file
#
# inspired by http://digital-sushi.org/entry/how-to-create-a-disk-image-installer-for-apple-mac-os-x/
#
# 1. create empty disk image
# hdiutil create -type SPARSE -fs HFS+ -volname CecogAnalyzer -layout NONE -size 10m CecogAnalyzer_template.sparseimage
#
# 2. mount image
# open CecogAnalyzer_template.sparseimage
#
# 3. make folder popup as separate window on mount automatically
# bless --folder /Volumes/CecogAnalyzer --openfolder /Volumes/CecogAnalyzer
#
# 4. change window size, background image, and icon. switch to icon view, set icon size to 128, insert link
#    to /Applications and create folder 'CecogAnalyzer.app' which is just a dummy for correct icon positioning
#
# 5. build CecogAnalyzer.app from setup.py and start this script with the version number as parameter
#

version=$1
volname="CecogAnalyzer-"$version
dmgfile="CecogAnalyzer_"$version"_MacOSX_Intel64.dmg"
tmp="temp.sparseimage"
appname="CecogAnalyzer.app"
appname2="CecogAnalyzer-"$version".app"

echo $version
echo $volname
echo $appname
echo $appname2
echo $dmgfile

# copy template to temp image which will be modified
cp CecogAnalyzer_template.sparseimage $tmp

# resize and mount image. FIXME: 90 MB could be to small in the future. size should be determined from .app
hdiutil resize -size 90m $tmp
hdiutil attach $tmp

# rename volume to take version into account
diskutil rename /Volumes/CecogAnalyzer $volname

# remove the dummy .app
rm -rf /Volumes/$volname/$appname

# copy new.app from dist/ sub-folder and preserve soft links
cp -RHp dist/$appname /Volumes/$volname/

# renaming of the .app did change positioning is skipped for now
#mv /Volumes/$volname/$appname /Volumes/$volname/$appname2

# eject temp image
hdiutil eject /Volumes/$volname

# convert temp image to a bzip2 compressed read-only .dmg file
hdiutil convert $tmp -ov -format UDBZ -o $dmgfile

# remove temp image
rm $tmp

# open final image
open $dmgfile

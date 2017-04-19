# The CellCognition Project
# Copyright (c) 2006 - 2012
# Gerlich Lab, IMBA Vienna, Austria
# www.cellcognition.org
# rudolf.hoefler@gmail.com
# 14/02/2013
# This software can be distribute under the term of the LGPL

VERSION = 1.6.1
ARCH=$$(uname -m)
APPNAME = CecogAnalyzer
TMPNAME = CecogAnalyzer.dmg
DMGNAME = CecogAnalyzer_$(VERSION)_$(ARCH).dmg
VOLNAME = $(APPNAME)-$(VERSION)

all: dmg

osx:
	python setup_mac.py py2app

dmg: osx
	hdiutil create -srcfolder dist/$(APPNAME).app \
	-volname $(VOLNAME) -fs HFS+ -format UDRW $(TMPNAME)
	hdiutil attach -readwrite -noverify -noautoopen $(TMPNAME)
	ln -s /Volumes/$(VOLNAME)/$(APPNAME).app/Contents/Resources/resources/battery_package/ /Volumes/$(VOLNAME)/battery_package
	ln -s /Applications /Volumes/$(VOLNAME)/Applications
	hdiutil detach /Volumes/$(VOLNAME)
	hdiutil convert $(TMPNAME) -format UDZO -imagekey zlib-level=6 -o $(DMGNAME)
	rm $(TMPNAME)
clean:
	rm -rfv build dist
	rm -fv *.dmg
	rm -fv *.*~
	rm -fv cecog/ccore/*.so

inplace:
	python setup.py build_rcc
	python setup.py build_help
	python setup.py build_ext --inplace

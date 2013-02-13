# The CellCognition Project
# Copyright (c) 2006 - 2012
# Gerlich Lab, IMBA Vienna, Austria
# www.cellcognition.org
# rudolf.hoefler@gmail.com
# 14/02/2013
# This software can be distribute under the term of the LGPL

VERSION = 1.4.0
APPNAME = CecogAnalyzer
DMGNAME = CecogAnalyzer-$(VERSION).dmg

all: dmg

osx:
	python setup_mac.py py2app
	mv dist/$(APPNAME).app dist/$(APPNAME)-$(VERSION).app

dmg: osx
	hdiutil create -srcfolder dist/$(APPNAME)-$(VERSION).app $(DMGNAME)

clean:
	rm -rfv build dist
	rm -fv $(DMGNAME)

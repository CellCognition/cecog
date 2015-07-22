"""
__init__.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

from PyQt5.QtCore import QFile
from PyQt5.QtCore import QTextStream


import classic_rc
import dark_blue_rc
import dark_orange_rc


StyleSheets = {'classic': ":/classic/style.qss",
               'dark blue': ":/dark_blue/style.qss",
               'dark orange': ":/dark_orange/style.qss",}

DefaultStyle = 'dark_blue'

def loadStyle(stylesheet):

    if stylesheet not in StyleSheets.keys():
        raise RuntimeError('Invalid stylesheet (%s)' %stylesheet)

    f = QFile(StyleSheets[stylesheet])
    f.open(QFile.ReadOnly | QFile.Text)
    ts = QTextStream(f)
    return  ts.readAll()

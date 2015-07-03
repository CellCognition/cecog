"""
aboutdialog.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from cecog import version


class CecogAboutDialog(QtWidgets.QDialog):

    def __init__(self, *args, **kw):
        super(CecogAboutDialog, self).__init__(*args, **kw)
        self.setBackgroundRole(QtGui.QPalette.Dark)
        self.setStyleSheet('background: #000000; '
                           'background-image: url(:cecog_about)')
        self.setWindowTitle('About CecogAnalyzer')
        self.setFixedSize(500, 300)
        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        label2 = QtWidgets.QLabel(self)
        label2.setStyleSheet('background: transparent;')
        label2.setTextFormat(Qt.AutoText)
        label2.setOpenExternalLinks(True)
        label2.setAlignment(Qt.AlignCenter)
        
        style = """
                background: transparent;
                color: white;
                a { color: white; } 
                a:visited { color: white;}
                """

        label2.setText('<span style="%s">CellCognition Analyzer GUI %s | Copyright (c) 2006 - 2015 | '
                       '<a style="color:white" href="http://cellcognition.org">cellcognition.org</a> | </span>' 
                       '<a style="color:white" href="https://github.com/CellCognition/cecog/issues">Bug tracker</a></span>' % (style, version.version)) 
        

        layout.addWidget(label2, 2, 0)
        layout.setAlignment(Qt.AlignCenter|Qt.AlignBottom)
        self.setLayout(layout)

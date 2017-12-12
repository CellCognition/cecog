"""
logwindow.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


__all__ = ('LogWindow', )


import logging

from .logger import LoggerObject
from .handlers import QHandler
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from cecog import version

class LogWindow(QtWidgets.QDialog):

    def __init__(self, parent, max_count=500, flags=Qt.Window):
        super(QtWidgets.QDialog, self).__init__(parent, flags)

        self.setWindowTitle("Application Log")
        self.setWindowModality(Qt.NonModal)
        self.resize(600, 430)
        self.max_count = max_count

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        self.handler = QHandler(self)
        self.handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
        self.handler.setFormatter(formatter)
        self.handler.messageReceived.connect(self.showMessage)

        logger = logging.getLogger()
        logger.addHandler(self.handler)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)

        toolbar = QtWidgets.QToolBar(self)
        toolbar.setObjectName('LoggerToolbar')
        toolbar.addWidget(QtWidgets.QLabel('Log level: ', self))
        combo = QtWidgets.QComboBox(self)
        combo.currentIndexChanged[str].connect(self.onLevelChanged)
        toolbar.addWidget(combo)
        layout.addWidget(toolbar)

        self.tabs = QtWidgets.QTabWidget(self)
        self.tabs.setUsesScrollButtons(True)

        layout.addWidget(self.tabs)

        for name in LoggerObject.Levels.names():
            combo.addItem(name)

        combo.setCurrentIndex(combo.findText("INFO"))

        self.hide()

    def _setupTextEdit(self):
        textedit = QtWidgets.QPlainTextEdit(self)
        textedit.setReadOnly(True)
        textedit.setMaximumBlockCount(self.max_count)
        format_ = QtGui.QTextCharFormat()
        format_.setFontFixedPitch(True)
        textedit.setCurrentCharFormat(format_)

        self.tabs.addTab(textedit, 'Main')
        return textedit

    def initProcessLogs(self, sub_process_names):
        self.clear()

        for p in sub_process_names:
            lw = QtWidgets.QPlainTextEdit(self.tabs)
            lw.setReadOnly(True)
            self.tabs.addTab(lw, str(p))
        self.tabs.setCurrentIndex(1)

    def onLevelChanged(self, name):
        self.handler.setLevel(getattr(LoggerObject.Levels, str(name)))

    def clear(self):
        self.tabs.clear()
        self._setupTextEdit()

    def findTabByName(self, name):

        for i in range(self.tabs.count()):
            if self.tabs.tabText(i).replace("&", "") == name:
                return self.tabs.widget(i)

        return self.tabs.widget(0)


    def showMessage(self, msg, level=None, name="Main"):

        if not self.isVisible():
            return

        if "." in name:
            name = name.split(".")[1]

        tv = self.findTabByName(name)

        if level == LoggerObject.Levels.DEBUG:
            msg = "<font color='green'>" + msg + '</font>'
        elif level == LoggerObject.Levels.WARNING:
            msg = "<font color='orange'><b>" + msg + '</b></font>'
            self.tabs.setCurrentWidget(tv)
        elif level == LoggerObject.Levels.ERROR:
            msg = "<font color='red'><b>" + msg + '</b></font>'
            self.tabs.setCurrentWidget(tv)
        else:
            msg = "<font color='black'>" + msg + '</font>'

        tv.appendHtml(msg.replace('\n', '<br>'))
        tv.moveCursor(QtGui.QTextCursor.End)

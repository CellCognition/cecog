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
        self.resize(800, 600)

        self.items = dict()

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
        self._setupTextEdit(max_count)

        layout.addWidget(self.tabs)

        for name in LoggerObject.Levels.names():
            combo.addItem(name)
        self.hide()

    def _setupTextEdit(self, max_count):
        textedit = QtWidgets.QPlainTextEdit(self)
        textedit.setReadOnly(True)
        textedit.setMaximumBlockCount(max_count)
        format_ = QtGui.QTextCharFormat()
        format_.setFontFixedPitch(True)
        textedit.setCurrentCharFormat(format_)

        self.items[None] = textedit
        self.tabs.addTab(textedit, 'Main')
        return textedit

    def initProcessLogs(self, sub_process_names):
        self.clear()
        for p in sub_process_names:
            lw = QtWidgets.QPlainTextEdit(self.tabs)
            lw.setReadOnly(True)
            self.items[p] = lw
            self.tabs.addTab(lw, str(p))
        self.tabs.setCurrentIndex(1)

    def onLevelChanged(self, name):
        self.handler.setLevel(getattr(LoggerObject.Levels, str(name)))

    def clear(self):
        self.items[None].clear()

        for i in xrange(1, self.tabs.count(), 1):
            self.tabs.removeTab(i)

        for key in self.items.keys():
            if key is not None:
                del self.items[key]

    def showMessage(self, msg, level=None, name=None):

        if not self.isVisible():
            return

        if level == LoggerObject.Levels.DEBUG:
            msg = "<font color='green'>" + msg + '</font>'
        elif level == LoggerObject.Levels.WARNING:
            msg = "<font color='orange'><b>" + msg + '</b></font>'
            self.tabs.setCurrentWidget(self.items[name])
        elif level == LoggerObject.Levels.ERROR:
            msg = "<font color='red'><b>" + msg + '</b></font>'
            self.tabs.setCurrentWidget(self.items[name])
        else:
            msg = "<font color='black'>" + msg + '</font>'

        name = str(name)
        if self.items.has_key(name):
            tv = self.items[name]
        else:
            tv = self.items[None]

        tv.appendHtml(msg.replace('\n', '<br>'))
        tv.moveCursor(QtGui.QTextCursor.End)

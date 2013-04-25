"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = ['LogWindow', 'GuiLogHandler']

import logging

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

class LogWindow(QFrame):

    LEVELS = {'DEBUG' : logging.DEBUG,
              'INFO'  : logging.INFO,
              'WARN'  : logging.WARNING,
              'ERROR' : logging.ERROR}

    def __init__(self, handler, max_count=500):
        QFrame.__init__(self)
        self.setWindowTitle('Log window')

        self._handler = handler
        self._handler.message_received.connect(self._on_message_received)

        layout = QGridLayout(self)
        layout.setContentsMargins(5,5,5,5)
        self._log_widget = QPlainTextEdit(self)
        self._log_widget.setReadOnly(True)
        self._log_widget.setMaximumBlockCount(max_count)
        format = QTextCharFormat()
        format.setFontFixedPitch(True)
        self._log_widget.setCurrentCharFormat(format)
        layout.addWidget(self._log_widget, 0, 0, 1, 4)
        layout.setColumnStretch(0,2)
        layout.setColumnStretch(3,2)

        layout.addWidget(QLabel('Log level', self), 1, 0, Qt.AlignRight)
        combo = QComboBox(self)
        layout.addWidget(combo, 1, 1, Qt.AlignLeft)
        self.connect(combo, SIGNAL('currentIndexChanged(const QString &)'),
                     self._on_level_changed)
        for name in sorted(self.LEVELS, key=lambda x: self.LEVELS[x]):
            combo.addItem(name)

        self._msg_buffer = []

    def hideEvent(self, event):
        logger = logging.getLogger()
        logger.removeHandler(self._handler)
        QFrame.hideEvent(self, event)

    def showEvent(self, event):
        logger = logging.getLogger()
        logger.addHandler(self._handler)
        QFrame.showEvent(self, event)

    def _on_message_received(self, msg):
        self._msg_buffer.append(str(msg))
        if self.isVisible():
            self._log_widget.appendPlainText('\n'.join(self._msg_buffer))
        self._msg_buffer = []

    def _on_level_changed(self, name):
        self._handler.setLevel(self.LEVELS[str(name)])

    def clear(self):
        self._msg_buffer = []
        self._log_widget.clear()


class GuiLogHandler(QObject, logging.Handler):

    message_received = pyqtSignal(str)

    def __init__(self, parent):
        self._mutex = QMutex()
        QObject.__init__(self, parent)
        logging.Handler.__init__(self)#, strm=self._history)

    def emit(self, record):
        try:
            msg = self.format(record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)
        self.message_received.emit(msg)

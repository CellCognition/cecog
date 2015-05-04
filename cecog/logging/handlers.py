"""
handlers.py

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


__all__ = ('QHandler', )


import logging
from PyQt4.QtCore import QObject, pyqtSignal


class QHandler(QObject, logging.Handler):

    messageReceived = pyqtSignal(str, int, str)

    def __init__(self, parent=None, level=logging.NOTSET):
        QObject.__init__(self, parent)
        logging.Handler.__init__(self, level)

    def emit(self, record):
        try:
            msg = self.format(record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)
        self.messageReceived.emit(msg, record.levelno, record.name)

# -*- coding: utf-8 -*-
"""
corethreads.py - base class  for all threads of the processing pipline
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['CoreThread']

import logging
import traceback
from PyQt4 import QtCore

class CoreThread(QtCore.QThread):

    foobar = QtCore.pyqtSignal("PyQt_PyObject")

    stage_info = QtCore.pyqtSignal(dict)
    analyzer_error = QtCore.pyqtSignal(str)

    def __init__(self, parent, settings):
        super(CoreThread, self).__init__(parent)
        self._logger = logging.getLogger(self.__class__.__name__)
        self._settings = settings
        self._abort = False
        self._mutex = QtCore.QMutex()
        self._stage_info = {'text': '',
                            'progress': 0,
                            'max': 0}
    @property
    def parent(self):
        return super(CoreThread, self).parent()

    def __del__(self):
        self._abort = True
        self.stop()
        self.wait()

    def _run(self):
        raise NotImplementedError

    def run(self):
        try:
            import pydevd
            pydevd.connected = True
            pydevd.settrace(suspend=False)
            print 'Thread enabled interactive eclipse debuging...'
        except:
            pass

        try:
            self._run()
        except Exception, e:
            # XXX
            if hasattr(e, 'msg'):
                # MultiprocessingExeption
                msg = e.msg
            else:
                msg = traceback.format_exc()
                traceback.print_exc()

            logger = logging.getLogger()
            logger.error(msg)
            self.analyzer_error.emit(msg)
            raise

    def set_abort(self, wait=False):
        self._mutex.lock()
        try:
            self._abort = True
        finally:
            self._mutex.unlock()
        if wait:
            self.wait()

    def get_abort(self):
        abort = self._abort
        return abort

    def set_stage_info(self, info):
        self._mutex.lock()
        try:
            self.stage_info.emit(info)
        finally:
            self._mutex.unlock()

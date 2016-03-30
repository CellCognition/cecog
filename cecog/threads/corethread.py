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

__all__ = ('CoreThread', 'StopProcessing')

import logging
import traceback

from PyQt5 import QtCore

from cecog import ccore


class StopProcessing(Exception):
    pass



class CoreThread(QtCore.QThread):

    status = QtCore.pyqtSignal('PyQt_PyObject')
    increment = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(str, str)
    aborted = QtCore.pyqtSignal()
    image_ready = QtCore.pyqtSignal(dict, str)


    def __init__(self, parent, settings):
        super(CoreThread, self).__init__(parent)
        self._logger = logging.getLogger(self.__class__.__name__)
        self._renderer = None
        self._settings = settings
        self._abort = False
        self._mutex = QtCore.QMutex()

    def run(self):
        # turn off vigra tiff warnings
        if not __debug__:
            ccore.turn_off()
            self._enable_eclipse_mt_debugging()
        try:
            self._run()
        except StopProcessing:
            pass
        except Exception, e:
            msg = traceback.format_exc(e)
            traceback.print_exc(e)
            logger = logging.getLogger()
            logger.error(msg)
            self.error.emit(msg, str(e))
            # can cause a sefault on macosx
            # raise

    def abort(self, wait=False):
        self._mutex.lock()
        try:
            self._abort = True
        finally:
            self._mutex.unlock()

        if wait:
            self.wait()
        self.aborted.emit()

    def is_aborted(self):
        return self._abort


    def statusUpdate(self, min=0, max=None, meta="", progress=None,
                     text='', interval=None, msleep=0, increment=False):
        msg = dict(text=text, min=min, max=max, meta=meta, progress=progress,
                   interval=interval)

        self.status.emit(msg)

        if interval and progress is not None:
            raise RuntimeError("Can not set progress and emit increment signal")

        if increment:
            self.increment.emit()

        self.msleep(msleep)

    @property
    def renderer(self):
        return self._renderer

    @renderer.setter
    def renderer(self, renderer):
        self._mutex.lock()
        try:
            self._renderer = renderer
        finally:
            self._mutex.unlock()

    @renderer.deleter
    def renderer(self):
        del self._renderer

    def interruption_point(self):
        if self._abort:
            raise StopProcessing()

    def show_image(self, images, message, stime=0):
        self.image_ready.emit(images, message)
        self.msleep(stime)

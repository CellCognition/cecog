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
from cecog import ccore

class StopProcessing(Exception):
    pass

class ProgressMsg(dict):

    def __init__(self, min=0, max=1, stage=0, meta="", progress=0, text=''):
        self['min'] = min
        self['max'] = max
        self['stage'] = stage
        self['meta'] = meta
        self['progress'] = progress
        self['text'] = text

    def increment_progress(self):
        self.progress += 1

    def __getattr__(self, attr):

        if self.has_key(attr):
            return self[attr]
        else:
            return super(ProgressMsg, self).__getattr__(attr)

    def __setattr__(self, attr, value):
        if self.has_key(attr):
            self[attr] = value
        else:
            super(ProgressMsg, self).__setattr__(attr, value)


class CoreThread(QtCore.QThread):

    stage_info = QtCore.pyqtSignal('PyQt_PyObject')
    analyzer_error = QtCore.pyqtSignal(str)
    image_ready = QtCore.pyqtSignal(dict, str)

    def __init__(self, parent, settings):
        super(CoreThread, self).__init__(parent)
        self._logger = logging.getLogger(self.__class__.__name__)
        self._renderer = None
        self._settings = settings
        self._abort = False
        self._mutex = QtCore.QMutex()
        self._stage_info = {'text': '',
                            'progress': 0,
                            'max': 0}

    def _enable_eclipse_mt_debugging(self):
        try:
            import pydevd
            pydevd.connected = True
            pydevd.settrace(suspend=False)
            print 'Thread enabled interactive eclipse debuging...'
        except:
            pass

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
            self.analyzer_error.emit(msg)
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

    def update_status(self, info, stime=0):
        self.stage_info.emit(info)
        self.msleep(stime)

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

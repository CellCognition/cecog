# -*- coding: utf-8 -*-
"""
analyzer_thread.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


import copy
from PyQt4 import QtCore
from cecog import ccore
from cecog.threads.corethread import CoreThread
from cecog.analyzer.core import AnalyzerCore

class AnalyzerThread(CoreThread):

    image_ready = QtCore.pyqtSignal(ccore.RGBImage, str, str)

    def __init__(self, parent, settings, imagecontainer):
        super(AnalyzerThread, self).__init__(parent, settings)
        self._renderer = None
        self._imagecontainer = imagecontainer
        self._buffer = {}

    def _run(self):
        for plate_id in self._imagecontainer.plates:
            analyzer = AnalyzerCore(plate_id, self._settings,
                                    copy.deepcopy(self._imagecontainer))
            result = analyzer.processPositions(self)
            learner = result['ObjectLearner']
            post_hdf5_link_list = result['post_hdf5_link_list']
            if len(post_hdf5_link_list) > 0:
                link_hdf5_files(sorted(post_hdf5_link_list))

        # make sure the learner data is only exported while we do sample picking
        if self._settings.get('Classification', 'collectsamples') and \
                not learner is None:
            learner.export()

    def set_renderer(self, name):
        self._mutex.lock()
        try:
            self._renderer = name
            self._emit(name)
        finally:
            self._mutex.unlock()

    def get_renderer(self):
        return self._renderer

    def set_image(self, name, image_rgb, info, filename=''):
        self._mutex.lock()
        self._buffer[name] = (image_rgb, info, filename)
        if name == self._renderer:
            self._emit(name)
        self._mutex.unlock()

    def _emit(self, name):
        if name in self._buffer:
            self.image_ready.emit(*self._buffer[name])

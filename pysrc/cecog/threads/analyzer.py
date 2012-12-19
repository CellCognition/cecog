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
from cecog.threads.link_hdf import link_hdf5_files
from cecog.analyzer.core import AnalyzerCore

class AnalyzerThread(CoreThread):

    image_ready = QtCore.pyqtSignal(ccore.RGBImage, str, str)

    def __init__(self, parent, settings, imagecontainer):
        super(AnalyzerThread, self).__init__(parent, settings)
        self._renderer = None
        self._imagecontainer = imagecontainer

    def _run(self):
        for plate_id in self._imagecontainer.plates:
            analyzer = AnalyzerCore(plate_id, self._settings,
                                    copy.deepcopy(self._imagecontainer))
            h5_links = analyzer.processPositions(self)
            if h5_links:
                link_hdf5_files(h5_links)

        # make sure the learner data is only exported while we do sample picking
        if self._settings.get('Classification', 'collectsamples') and \
                not learner is None:
            learner.export()

    def set_renderer(self, name):
        self._mutex.lock()
        try:
            self._renderer = name
        finally:
            self._mutex.unlock()

    def get_renderer(self):
        return self._renderer

    def set_image(self, name, image, message, filename='', stime=0):
        if name == self._renderer:
            self.image_ready.emit(image, message, filename)
        self.msleep(stime)

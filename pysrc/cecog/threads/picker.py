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
from cecog.analyzer.core import Picker

class PickerThread(CoreThread):

    image_ready = QtCore.pyqtSignal(ccore.RGBImage, str, str)

    def __init__(self, parent, settings, imagecontainer):
        super(PickerThread, self).__init__(parent, settings)
        self._imagecontainer = imagecontainer

    def _run(self):
        learner = None
        for plate in self._imagecontainer.plates:
            picker = Picker(plate, self._settings,
                            copy.deepcopy(self._imagecontainer),
                            learner=learner)
            picker.processPositions(self)
            learner = picker.learner
        learner.export()

    def set_image(self, name, image, message, filename='', stime=0):
        self.image_ready.emit(image, message, filename)
        self.msleep(stime)

    def set_renderer(self, name):
        self._mutex.lock()
        try:
            self._renderer = name
        finally:
            self._mutex.unlock()

    def get_renderer(self):
        return self._renderer

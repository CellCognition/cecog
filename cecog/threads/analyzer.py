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

__all__ = ['AnalyzerThread']


import os
import copy
from cecog.threads.corethread import CoreThread
from cecog.analyzer.plate import PlateAnalyzer
from cecog.io.hdf import mergeHdfFiles

class AnalyzerThread(CoreThread):

    def __init__(self, parent, settings, imagecontainer):
        super(AnalyzerThread, self).__init__(parent, settings)
        self._imagecontainer = imagecontainer

    def _run(self):

        nplates = len(self._imagecontainer.plates)
        for plate in self._imagecontainer.plates:
            analyzer = PlateAnalyzer(plate, self._settings,
                                     copy.deepcopy(self._imagecontainer))

            # set maxium in the progress bar
            imax = len(analyzer.frames)*len(analyzer.positions)*nplates
            self.statusUpdate(min=0, max=imax)
            analyzer()

        # merge hdf files into one
        mergeHdfFiles(analyzer.h5f, analyzer.ch5dir, remove_source=True)
        os.rmdir(analyzer.ch5dir)

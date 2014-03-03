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


import copy
from cecog.threads.corethread import CoreThread
from cecog.threads.link_hdf import link_hdf5_files
from cecog.analyzer.core import AnalyzerCore


class AnalyzerThread(CoreThread):

    def __init__(self, parent, settings, imagecontainer):
        super(AnalyzerThread, self).__init__(parent, settings)
        self._imagecontainer = imagecontainer

    def _run(self):

        for plate_id in self._imagecontainer.plates:
            analyzer = AnalyzerCore(plate_id, self._settings,
                                    copy.deepcopy(self._imagecontainer))
            h5_links = analyzer.processPositions(self)
            if h5_links:
                link_hdf5_files(h5_links)

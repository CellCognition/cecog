"""
picker.py

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


import copy
from cecog.threads.corethread import CoreThread
from cecog.analyzer.core import Picker

class PickerThread(CoreThread):

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

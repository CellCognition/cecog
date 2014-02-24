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

from cecog.learning.learning import CommonObjectLearner
from cecog import CH_PRIMARY, CH_OTHER, CH_VIRTUAL
from cecog.util.ctuple import COrderedDict

class PickerThread(CoreThread):

    def __init__(self, parent, settings, imagecontainer):
        super(PickerThread, self).__init__(parent, settings)
        self._imagecontainer = imagecontainer

    def _channel_regions(self, pchannel, chid):
        """Return a dict that contains the processing channel an the region
        used for feature extraction."""
        regions = COrderedDict()
        if chid is None:
            for prefix in (CH_PRIMARY+CH_OTHER):
                if self._settings.get("Classification", "merge_%s" %prefix):
                    regions[prefix.title()] = \
                        self._settings.get("Classification", "%s_%s_region"
                                          %(CH_VIRTUAL[0], prefix))
        else:
            regions[pchannel.title()] = self._settings.get( \
                'Classification', "%s_classification_regionname" %pchannel)
        return regions

    def _setup_learner(self):
        """Return the CommonObjectLearner instance, set up according to
        processing channel and its settings."""

        pchannel = self._settings.get("Classification", "collectsamples_prefix")
        chid = self._settings.get("ObjectDetection", "%s_channelid" %(pchannel))
        cpath = self._settings.get("Classification",
                                    "%s_classification_envpath" %pchannel)

        learner = CommonObjectLearner(cpath,
                                      pchannel.title(),
                                      self._channel_regions(pchannel, chid),
                                      chid,
                                      has_zero_insert=False)
        learner.loadDefinition()
        return learner

    def _run(self):
        frame_count = 0
        learner = self._setup_learner()
        for plate in self._imagecontainer.plates:
            picker = Picker(plate, self._settings,
                            copy.deepcopy(self._imagecontainer),
                            learner=learner)
            picker.processPositions(self)
            learner = picker.learner
            frame_count =+ len(picker.positions)

        if frame_count == 0:
            raise RuntimeError("Didn't pick any samples from 0 frames. Check plate names")


        if not self.is_aborted():
            learner.export()

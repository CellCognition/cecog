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

__all__ = ('TrainerThread', )


import os
import copy

from cecog.classifier import SupportVectorClassifier
from cecog.analyzer.plate import Trainer
from cecog.threads.corethread import CoreThread

from cecog import CH_PRIMARY, CH_OTHER, CH_VIRTUAL
from cecog.util.ctuple import COrderedDict


class TrainerThread(CoreThread):

    def __init__(self, parent, settings, imagecontainer):
        super(TrainerThread, self).__init__(parent, settings)
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

    def _setup_trainer(self):

        pchannel = self._settings.get("Classification", "collectsamples_prefix")
        chid = self._settings.get("ObjectDetection", "%s_channelid" %(pchannel))

        cpath = self._settings.get(
            "Classification", "%s_classification_envpath" %pchannel)

        if not chid:
            chid = None

        return SupportVectorClassifier(
            cpath, pchannel.title(), self._channel_regions(pchannel, chid), chid)

    def _run(self):
        frame_count = 0
        classifier = self._setup_trainer()

        for plate in self._imagecontainer.plates:
            trainer = Trainer(
                plate, self._settings, copy.deepcopy(self._imagecontainer),
                learner=classifier)
            trainer()
            classifier = trainer.learner
            frame_count += len(trainer.positions)

        if frame_count == 0:
            raise RuntimeError("Didn't pick any samples from 0 frames. Check plate names")

        self.interruption_point()
        self.statusUpdate(progress=0, max=-1, text="Performing Grid Search...")
        classifier.save()
        self.statusUpdate(progress=0, max=1, text="Classifier training finished")

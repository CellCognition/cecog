"""
training.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


__all__ = ("PosTrainer", )


from PyQt5.QtCore import QThread

from .analysis import PositionCore
from cecog.util.stopwatch import StopWatch
from cecog.io.imagecontainer import Coordinate
from cecog.analyzer.timeholder import TimeHolder
from cecog.analyzer.analyzer import CellAnalyzer
from cecog.threads.corethread import ProgressMsg



class PosTrainer(PositionCore):

    def __call__(self):

        self.timeholder = TimeHolder(self.position, self._all_channel_regions,
                                     None,
                                     self.meta_data, self.settings,
                                     self._frames,
                                     self.plate_id,
                                     **self._hdf_options)

        ca = CellAnalyzer(timeholder=self.timeholder,
                          position = self.position,
                          create_images = True,
                          binning_factor = 1,
                          detect_objects = self.settings.get('Processing',
                                                             'objectdetection'))
        self._analyze(ca)

    def _analyze(self, cellanalyzer):

        thread = QThread.currentThread()
        imax = sum([len(n) for n in self.sample_positions.values()])

        prg = ProgressMsg(min=1, max=imax, meta="Classifier training: ")

        stopwatch = StopWatch(start=True)
        crd = Coordinate(self.plate_id, self.position,
                         self._frames, list(set(self.ch_mapping.values())))

        for frame, channels in self._imagecontainer( \
            crd, interrupt_channel=True, interrupt_zslice=True):

            thread.interruption_point()
            prg.text = '%s, %s, T %d, (%d/%d)' \
                       %(self.plate_id, self.position,
                         frame, self._frames.index(frame)+1, len(self._frames))

            prg.interval = stopwatch.interim()
            thread.update_status(prg)


            stopwatch.reset(start=True)
            # initTimepoint clears channel_registry
            cellanalyzer.initTimepoint(frame)
            self.register_channels(cellanalyzer, channels)

            cellanalyzer.collectObjects(self.plate_id, self.position, self.sample_readers,
                                        self.learner)

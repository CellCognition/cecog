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


__all__ = ("PositionPicker", )


from cecog.io.imagecontainer import Coordinate
from cecog.analyzer.timeholder import TimeHolder
from cecog.analyzer.analyzer import CellAnalyzer
from cecog.util.stopwatch import StopWatch
from .analysis import PositionCore



class PositionPicker(PositionCore):

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

        self._info.update({'stage': 2,
                           'min': 1,
                           'max': len(self._frames),
                           'meta' : 'Classifier training:',
                           'item_name': 'image set'})


        stopwatch = StopWatch(start=True)
        crd = Coordinate(self.plate_id, self.position,
                         self._frames, list(set(self.ch_mapping.values())))

        for frame, channels in self._imagecontainer( \
            crd, interrupt_channel=True, interrupt_zslice=True):

            if self.is_aborted():
                return
            else:
                txt = 'T %d (%d/%d)' %(frame, self._frames.index(frame)+1,
                                       len(self._frames))
                self.update_status({'progress': self._frames.index(frame)+1,
                                    'text': txt,
                                    'interval': stopwatch.interim()})

            stopwatch.reset(start=True)
            # initTimepoint clears channel_registry
            cellanalyzer.initTimepoint(frame)
            self.register_channels(cellanalyzer, channels)

            cellanalyzer.collectObjects(self.plate_id, self.position, self.sample_readers,
                                        self.learner)

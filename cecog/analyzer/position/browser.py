"""
browser.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


__all__ = ("PositionAnalyzerForBrowser", )

import os
from os.path import join, basename

from cecog.util.stopwatch import StopWatch
from cecog.io.imagecontainer import Coordinate
from cecog.analyzer.timeholder import TimeHolder
from cecog.analyzer.analyzer import CellAnalyzer
from cecog.svc import SVCPredictor
from .analysis import PositionCore


class PositionAnalyzerForBrowser(PositionCore):

    def __init__(self, *args, **kw):
        super(PositionAnalyzerForBrowser, self).__init__(*args, **kw)
        # Also in the Browser we want to use cellh5
        # The setting for the other PositionAnalyszer is
        # implicitely set in _makedirs()
        self._hdf5_dir = os.path.join(self._out_dir, 'hdf5')

    @property
    def _hdf_options(self):
        self.settings.set_section('Output')
        h5opts = {"hdf5_include_tracking": False,
                  "hdf5_include_events": False,
                  "hdf5_compression": False,
                  "hdf5_create": False,
                  "hdf5_reuse": self.settings.get2('hdf5_reuse'),
                  "hdf5_include_raw_images": False,
                  "hdf5_include_label_images": False,
                  "hdf5_include_features": False,
                  "hdf5_include_crack": False,
                  "hdf5_include_classification": False}

        return h5opts


    def setup_classifiers(self):
        sttg = self.settings
        # processing channel, color channel
        for p_channel, c_channel in self.ch_mapping.iteritems():
            if sttg('Processing', self._resolve_name(p_channel, 'classification')):
                cpath = sttg('Classification', self._resolve_name(p_channel, 'classification_envpath'))
                cpath = join(cpath, basename(cpath)+".hdf")
                try:
                    svc = SVCPredictor(cpath, load=True,
                                       channels=self._channel_regions(p_channel),
                                       color_channel=c_channel)
                except IOError as e:
                    pass
                else:
                    svc.close()
                    self.classifiers[p_channel] = svc


    def __call__(self):
        hdf5_fname = join(self._hdf5_dir, '%s.ch5' % self.position)

        self.timeholder = TimeHolder(self.position, self._all_channel_regions,
                                     hdf5_fname,
                                     self.meta_data, self.settings,
                                     self._frames,
                                     self.plate_id,
                                     **self._hdf_options)


        stopwatch = StopWatch(start=True)
        ca = CellAnalyzer(timeholder=self.timeholder,
                          position = self.position,
                          create_images = True,
                          binning_factor = 1,
                          detect_objects = self.settings.get('Processing', 'objectdetection'))

        self._analyze(ca)
        return ca

    def setup_channel(self, proc_channel, col_channel, zslice_images,
                      check_for_plugins=False):
        return super(PositionAnalyzerForBrowser, self).setup_channel(
            proc_channel, col_channel, zslice_images, False)

    def _analyze(self, cellanalyzer):
        n_images = 0
        stopwatch = StopWatch(start=True)
        crd = Coordinate(self.plate_id, self.position,
                         self._frames, list(set(self.ch_mapping.values())))


        for frame, channels in self._imagecontainer( \
            crd, interrupt_channel=True, interrupt_zslice=True):

            if self.is_aborted():
                self.clear()
                return 0
            else:
                txt = 'T %d (%d/%d)' %(frame, self._frames.index(frame)+1,
                                       len(self._frames))
                self.update_status({'progress': self._frames.index(frame)+1,
                                    'text': txt,
                                    'interval': stopwatch.interim()})

            stopwatch.reset(start=True)
            cellanalyzer.initTimepoint(frame)

            self.register_channels(cellanalyzer, channels)

            cellanalyzer.process()
            self.setup_classifiers()

            for chname, clf in self.classifiers.iteritems():
                try:
                    cellanalyzer.classify_objects(clf, chname)
                except KeyError as e:
                    pass

        return n_images

"""
plate.py

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


__all__ = ("Trainer", "PlateAnalyzer", "AnalyzerBrowser")

import os
import re
import glob
import traceback
from os.path import join, basename, isfile

from cecog.io import Ch5File
from cecog.util.util import makedirs
from cecog.logging import LoggerObject
from cecog.threads import StopProcessing
from cecog.classifier import AnnotationsFile
from cecog.gui.preferences import AppPreferences
from cecog.analyzer.position import PositionAnalyzer
from cecog.analyzer.position import PositionAnalyzerForBrowser
from cecog.analyzer.position import PosTrainer
from cecog.io.imagecontainer import MetaImage



class Analyzer(LoggerObject):

    def __init__(self, plate, settings, imagecontainer):
        super(Analyzer, self).__init__()
        self._frames = None
        self._positions = None

        self.sample_reader = list()
        self.sample_positions = dict()

        self.add_stream_handler(self.Levels.WARNING)
        self._imagecontainer = imagecontainer
        self.settings = settings
        self.plate = plate
        self._imagecontainer.set_plate(plate)

    @property
    def _outdir(self):
        return self._imagecontainer.get_path_out(self.plate)

    @property
    def meta_data(self):
        return self._imagecontainer.get_meta_data()

    @property
    def frames(self):
        """Return a list of frame indices under consideration of time
        constraints (start, end, increment)
        """

        if self._frames is None:
            frames_total = self.meta_data.times
            f_start, f_end, f_incr = 0, len(frames_total), 1

            if self.settings.get('General', 'frameRange'):
                f_incr = self.settings.get('General', 'frameincrement')
                try:
                    fmin = max(min(frames_total),
                               self.settings('General', 'frameRange_begin'))
                    fmax = min(max(frames_total),
                               self.settings('General', 'frameRange_end'))
                    f_start = frames_total.index(fmin)
                    f_end = frames_total.index(fmax)
                except ValueError:
                    # this can happen if coordinates have already a
                    # increment > 1
                    msg = ("Time constraint: either 'Begin' or 'End' "
                           "is an invalid value!")
                    raise ValueError(msg)

                if f_start > f_end:
                    raise RuntimeError(("Invalid time constraints "
                                        "(Begin < End)!"))

                self._frames = frames_total[f_start:f_end+1:f_incr]
            else:
                self._frames = frames_total

        return self._frames


class PlateAnalyzer(Analyzer):

    def __init__(self, plate, settings, imagecontainer, mode="w"):
        super(PlateAnalyzer, self).__init__(plate, settings, imagecontainer)
        self._makedirs()

        self.h5f = join(self._outdir, "%s.ch5" %plate)

        # don't overwrite file
        if settings('General', 'skip_finished'):
            mode = "r+"

        with Ch5File(self.h5f, mode=mode) as ch5:
            if not ch5.hasLayout(plate):
                layout = "%s/%s.txt" %(settings("General", "plate_layout"), plate)
                ch5.savePlateLayout(layout, plate)

        self._setup_cropping()

        self.logger.debug("frames: %r" % self.frames)

    @property
    def ch5dir(self):
        return self._cellh5_dir

    def _makedirs(self):

        odirs = (join(self._outdir, "cellh5"), )

        if AppPreferences().write_logs:
            odirs += (join(self._outdir, "log"), )


        for odir in odirs:
            try:
                makedirs(odir)
            except os.error: # no permissions
                self.logger.error("mkdir %s: failed" %odir)
            else:
                self.logger.info("mkdir %s: ok" %odir)
            setattr(self, "_%s_dir" %basename(odir.lower()).strip("_"), odir)


    @property
    def positions(self):
        """Determine positions to process considering

        -) constrain position
        -) skip already processed
        """

        if self._positions is None:
            if self.settings.get('General', 'constrain_positions'):
                positions  = self.settings.get('General', 'positions').split(',')
            else:
                positions = list(self.meta_data.positions)

            if not set(positions).issubset(self.meta_data.positions):
                raise ValueError(("The list of selected positions is not valid!"
                                  " %s\nValid values are %s" % \
                                      (positions, self.meta_data.positions)))

            self._positions = sorted(positions)

        return self._positions

    @positions.setter
    def positions(self, positions):
        assert isinstance(positions, list)
        self._positions = sorted(positions)

    def _setup_cropping(self):
        crop = self.settings.get('General', 'crop_image')
        x0 = self.settings.get('General', 'crop_image_x0')
        y0 = self.settings.get('General', 'crop_image_y0')
        x1 = self.settings.get('General', 'crop_image_x1')
        y1 = self.settings.get('General', 'crop_image_y1')

        if crop:
            MetaImage.enable_cropping(x0, y0, x1-x0, y1-y0)
            self.logger.info("cropping enabled with %d %d %d %d"
                             % (x0, y0, x1-x0, y1-y0))
        else:
            MetaImage.disable_cropping()
            self.logger.info("cropping disabled")

    def __call__(self):

        with Ch5File(self.h5f, mode="r") as ch5:
            finished = ch5.existingSites(self.plate)
            layout = ch5.layout(self.plate)

        for pos in self.positions:
            i = layout["File"].tolist().index(pos)
            well, site = layout["Well"][i], layout["Site"][i]
            wsstr = "%s_%02d" %(well, site)

            if well in finished and str(site) in finished[well] and self.settings(
                    'General', 'skip_finished'):
                msg = 'Skipping already processed postion %s' %wsstr
                self.logger.info(msg)
                continue
            else:
                self.logger.info('Processing position: %s' %wsstr)

            datafile = join(self._cellh5_dir, '%s.ch5' %wsstr)
            analyzer = PositionAnalyzer(
                self.plate, pos, datafile, self.settings, self.frames,
                self.sample_reader, self.sample_positions, None,
                self._imagecontainer, layout, AppPreferences().write_logs)

            try:
                analyzer()
                with Ch5File(self.h5f, mode="r+") as ch5:
                    if isfile(analyzer.datafile):
                        ch5.createSite(analyzer.datafile)
            except StopProcessing:
                pass
            except Exception as e:
                traceback.print_exc()
                raise
            finally:
                analyzer.clear()


class AnalyzerBrowser(PlateAnalyzer):

    def __init__(self, plate, settings, imagecontainer, mode="a"):
        super(AnalyzerBrowser, self).__init__(plate, settings, imagecontainer, mode)

    def __call__(self):

        pos = self.positions[0]
        self.logger.info('Browser(): Process positions: %r' % pos)
        analyzer = PositionAnalyzerForBrowser(
            self.plate, pos, self._outdir, self.settings,
            self.frames, self.sample_reader, self.sample_positions,
            None, self._imagecontainer, layout=None, writelogs=False)

        analyzer.add_stream_handler()
        return analyzer()


class Trainer(Analyzer):

    def __init__(self, plate, settings, imagecontainer, learner):
        super(Trainer, self).__init__(plate, settings, imagecontainer)

        # belongs already to picker
        self.sample_reader = []
        self.sample_positions = {}
        self.learner = learner

        pattern = join(self.learner.annotations_dir, "*.xml")
        anno_re = re.compile(('((.*?_{1,3})?PL(?P<plate>.*?)_{2,3})?P(?P'
                              '<position>.+?)_{2,3}T(?P<time>\d+).*?'))

        frames_total = self.meta_data.times

        for annofile in glob.glob(pattern):

            result = anno_re.match(basename(annofile))
            if result is None:
                msg = ("Something is wrong with your annotation files in "
                       "the classifier folder. Please make sure that the "
                       "XML have consistent plate names.")
                raise RuntimeError(msg)

            # Taking only annotated samples for the specific plate
            if (result.group("plate") != self.plate):
                continue
            elif self.is_valid_annofile(result):
                reader = AnnotationsFile(result, annofile, frames_total)
                self.sample_reader.append(reader)

                position = result.group('position')
                if not position in self.sample_positions:
                    self.sample_positions[position] = []
                self.sample_positions[position].extend(reader.timepoints())
            else:
                raise RuntimeError("Annotation file is invalid!")

        for pos, iframes in self.sample_positions.iteritems():
            self.sample_positions[pos] = sorted(list(set(iframes)))
        self.positions = self.sample_positions.keys()

    def is_valid_annofile(self, result):
        # sanity checks for the annotation file
        if result is None:
            raise RuntimeError(("Annotation file name does not match the "
                                "plate name"))
        elif result.group("plate") is None:
            raise RuntimeError("Plate name does is invalid (%s, %s)"
                               %(result.group("plate"), self.plate))
        return True


    def __call__(self):

        for pos, frames in self.sample_positions.iteritems():
            self.logger.info('Process positions: %r' %pos)

            postrainer = PosTrainer(self.plate, pos, self._outdir,
                                    self.settings,
                                    frames, self.sample_reader,
                                    self.sample_positions, self.learner,
                                    self._imagecontainer, layout=None)
            postrainer()

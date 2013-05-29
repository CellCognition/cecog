"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

import os
import re
import glob
from os.path import join, basename, isdir

from cecog.learning.collector import CellCounterReader, CellCounterReaderXML
from cecog.analyzer.position import PositionAnalyzer
from cecog.analyzer.position import PositionPicker
from cecog.io.imagecontainer import MetaImage
from cecog.util.logger import LoggerObject
from cecog.util.util import makedirs

# XXX - fix class names
class AnalyzerBase(LoggerObject):

    def __init__(self, plate, settings, imagecontainer):
        super(AnalyzerBase, self).__init__()
        self._frames = None
        self._positions = None

        # XXX
        self.sample_reader = list()
        self.sample_positions = dict()

        self.add_stream_handler(self._lvl.WARNING)
        self._imagecontainer = imagecontainer
        self.settings = settings
        self.plate = plate
        self._imagecontainer.set_plate(plate)

    @property
    def _out_dir(self):
        return self._imagecontainer.get_path_out(self.plate)

    @property
    def meta_data(self):
        return self._imagecontainer.get_meta_data()

    def _makedirs(self):
        """Make output directories (analyzed, dumps and log)"""
        odirs = ("analyzed", "hdf5", "plots", "log")
        for odir in odirs:
            path = join(self._out_dir, odir)
            try:
                makedirs(path)
            except os.error: # no permissions
                self.logger.error("mkdir %s: failed" %path)
            else:
                self.logger.info("mkdir %s: ok" %path)
            setattr(self, "_%s_dir" %basename(odir).lower(), path)

    @property
    def frames(self):
        """Return a list of frame indices under consideration of time
        constraints (start, end, increment)
        """

        if self._frames is None:
            frames_total = self.meta_data.times
            f_start, f_end, f_incr = 1, len(frames_total), 1

            if self.settings.get('General', 'frameRange'):
                f_start = max(self.settings.get('General', 'frameRange_begin'),
                              f_start)
                f_end = min(self.settings.get('General', 'frameRange_end'),
                            f_end)
                f_incr = self.settings.get('General', 'frameincrement')

                # > for picking >= anything else
                if f_start > f_end:
                    raise RuntimeError(("Invalid time constraints "
                                        "(upper_bound <= lower_bound)!"))
                self._frames = frames_total[f_start-1:f_end:f_incr]
            else:
                self._frames = frames_total
        return self._frames


class AnalyzerCore(AnalyzerBase):

    def __init__(self, plate, settings, imagecontainer):
        super(AnalyzerCore, self).__init__(plate, settings, imagecontainer)
        self._makedirs()
        self._setup_cropping()
        self.logger.info("openening image container: end")
        self.logger.info("lstAnalysisFrames: %r" % self.frames)

    def _already_processed(self, positions):
        """Find positions already been processed and remove them from list"""
        _finished_dir = join(self._log_dir, '_finished')
        set_found = set()
        positions = set(positions)
        if isdir(_finished_dir):
            for file_ in glob.glob(join("%s" %_finished_dir, "*.txt")):
                fname = basename(file_)
                if fname.startswith("_"):
                    pos = fname.split('_')[1]
                else:
                    pos = fname.split('__')[0]
                set_found.add(pos)
                pos_found = list(positions.difference(set_found))
            pos_found.sort()
            self.logger.info(("Following positions have been "
                              "processed already:\n%s" %positions))
        else:
            pos_found = positions
            self.logger.info("No positions have been processed yet.")
        return pos_found

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

            # drop already processed positions
            if self.settings.get('General', 'redoFailedOnly'):
                positions = self._already_processed(positions)
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

    def processPositions(self, qthread=None, myhack=None):
        job_args = []
        for pos in self.positions:
            self.logger.info('Process positions: %r' % pos)
            if len(self.frames) > 0:
                args_ = (self.plate,
                         pos,
                         self._out_dir,
                         self.settings,
                         self.frames,
                         self.sample_reader,
                         self.sample_positions,
                         None,
                         self._imagecontainer)
                kw_ = dict(qthread = qthread, myhack = myhack)
                job_args.append((args_, kw_))

        stage_info = {'stage': 1, 'min': 1, 'max': len(job_args)}

        hdf5_links = []
        for idx, (args_, kw_) in enumerate(job_args):
            if not qthread is None:
                if qthread.is_aborted():
                    break
                stage_info.update({'progress': idx+1,
                                   'text': 'P %s (%d/%d)' \
                                       % (args_[0], idx+1, len(job_args))})
                qthread.update_status(stage_info)
            analyzer = PositionAnalyzer(*args_, **kw_)
            try:
                nimages = analyzer()
            finally:
                analyzer.clear()

            if self.settings.get('Output', 'hdf5_create_file') and \
                    self.settings.get('Output', 'hdf5_merge_positions'):
                hdf5_links.append(analyzer.hdf5_filename)
        return hdf5_links


class Picker(AnalyzerBase):

    def __init__(self, plate, settings, imagecontainer, learner):
        super(Picker, self).__init__(plate, settings, imagecontainer)

        # belongs already to picker
        self.sample_reader = []
        self.sample_positions = {}
        self.learner = learner

        pattern = join(self.learner.annotations_dir, "*%s" %learner.extension)
        anno_re = re.compile(('((.*?_{1,3})?PL(?P<plate>.*?)_{1,3})?P(?P'
                              '<position>.+?)_{1,3}T(?P<time>\d+).*?'))

        frames_total = self.meta_data.times
        for annofile in glob.glob(pattern):

            result = anno_re.match(basename(annofile))
            if result is None:
                raise RuntimeError("Something is wrong with your annotation files in the classifier folder. " +
                                   "Please make sure that the XML have consistent plate names.")

            # Taking only annotated samples for the specific plate
            if (result.group("plate") != self.plate):
                continue
            elif self.is_valid_annofile(result):
                if learner.extension.endswith(learner.XML):
                    reader = CellCounterReaderXML(result, annofile, frames_total)
                else:
                    reader = CellCounterReader(result, annofile, frames_total)
                self.sample_reader.append(reader)

                position = result.group('position')
                if not position in self.sample_positions:
                    self.sample_positions[position] = []
                self.sample_positions[position].extend(reader.getTimePoints())
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


    def processPositions(self, qthread=None, myhack=None):
        imax = len(self.sample_positions)

        for i, (posid, frames) in enumerate(self.sample_positions.iteritems()):
            self.logger.info('Process positions: %r' %posid)

            if not qthread is None:
                if qthread.is_aborted():
                    break
                qthread.update_status({'stage': 1, 'min': 1,
                                       "max": imax, 'progress': i+1,
                                       'text': 'P %s (%d/%d)' \
                                           %(self.plate, i+1, imax)})

            picker = PositionPicker(self.plate, posid, self._out_dir,
                                    self.settings,
                                    frames, self.sample_reader,
                                    self.sample_positions, self.learner,
                                    self._imagecontainer, qthread, myhack)
            result = picker()

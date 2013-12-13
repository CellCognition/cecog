"""
runner.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Michael Held'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['PlateMapping', 'PositionRunner', 'PlateRunner']

import os
import glob
import traceback
import numpy as np

from os.path import join, isfile, isdir, basename
from PyQt4 import QtCore
from PyQt4.QtCore import QThread

from cecog.util.util import makedirs
from cecog.export.regexp import re_events
from cecog.threads.corethread import ProgressMsg
from cecog.errorcorrection.hmm import HmmSklearn as Hmm
from cecog.errorcorrection import HmmReport
from cecog.errorcorrection import PlateMapping
from cecog.errorcorrection.datatable import HmmDataTable
from cecog.gallery import MultiChannelGallery


class PlateRunner(QtCore.QObject):

    progressUpdate = QtCore.pyqtSignal(dict)

    def __init__(self, plates, outdirs, params_ec, *args, **kw):
        super(PlateRunner, self).__init__(*args, **kw)
        self.plates = plates
        self._outdirs = dict([(p, d) for p, d in zip(plates, outdirs)])
        self.params_ec = params_ec
        self._is_aborted = False

    def abort(self):
        self._is_aborted = True

    def _check_mapping_files(self):
        """Check plate mappings files for existence."""
        for plate in self.plates:
            mpfile = join(self.params_ec.mapping_dir, '%s.txt' %plate)
            if not isfile(mpfile):
                raise IOError('Mapping file not found\n(%s)' %mpfile)

    def __call__(self):
        if self.params_ec.position_labels:
            self._check_mapping_files()

        progress = ProgressMsg(max=len(self.plates), meta="Error correction...")

        for i, plate in enumerate(self.plates):
            QThread.currentThread().interruption_point()
            progress.text = ("Plate: '%s' (%d / %d)"
                             %(plate, i+1, len(self.plates)))
            self.progressUpdate.emit(progress)
            runner = PositionRunner(plate, self._outdirs[plate],
                                    self.params_ec, parent=self)
            runner()
            self.progressUpdate.emit(progress)

class PositionRunner(QtCore.QObject):

    def __init__(self, plate, outdir, ecopts, positions=None, parent=None,
                 *args, **kw):
        super(PositionRunner, self).__init__(parent, *args, **kw)
        self.ecopts = ecopts # error correction options
        self.plate = plate
        self._outdir = outdir

        self._channel_dirs = dict()
        self._makedirs()

        self.positions = positions
        if positions is None:
            self.positions = self._listdirs(self._analyzed_dir)

    def _listdirs(self, path):
        return sorted([x for x in os.listdir(path)
                       if isdir(join(path, x)) and not x.startswith('_')])

    def _makedirs(self):
        """Create/setup output directories.

        -) <analyzed-dir>/analyzed (already exists)
        -) <analysis-dir>/hmm
        -) <analysis-dir>/hmm/gallery
        """
        assert isinstance(self._outdir, basestring)
        self._analyzed_dir = join(self._outdir, "analyzed")

        odirs = (join(self._outdir, "hmm"),
                 join(self._outdir, "hmm", "gallery"))
        for odir in odirs:
            try:
                makedirs(odir)
            except os.error: # no permissions
                raise OSError("Missing permissions to create dir\n(%s)" %odir)
            else:
                setattr(self, "_%s_dir" %basename(odir.lower()).strip("_"), odir)

    def _gallery_image(self, pos, groupdict, channel, ext='png'):
        fname = ("P%(position)s__T%(time)s__O%(object)s__B%(branch)s."
                 "%(ext)s" %dict({'ext': ext}.items() + groupdict.items()))
        fname = join(self._analyzed_dir, pos, 'gallery', channel, fname)
        if isfile:
            return fname

    def _load_data(self, mappings, channel, classdef):
        # XXX perhaps the data table should also implement the import
        # --> having a data table for csv and cellh5...
        dtable = HmmDataTable()

        for pi, pos in enumerate(self.positions):
            dtable.add_position(pos, mappings[pos])
            files = glob.glob(join(self._analyzed_dir, pos, 'statistics',
                                   'events')+os.sep+"*.txt")
            progress = ProgressMsg(max=len(files),
                                   meta="loading plate: %s, position:%s, (%d/%d)"
                                   %(self.plate, pos, pi+1, len(self.positions)))

            for i, file_ in enumerate(files):
                QThread.currentThread().interruption_point()
                matched = re_events.match(basename(file_))
                try:
                    ch = matched.group('channel')
                    branch = matched.group('branch')
                except AttributeError:
                    pass
                else:
                    progress.increment_progress()
                    if self.ecopts.ignore_tracking_branches and branch != '01':
                        continue
                    progress.text = basename(file_)
                    self.parent().progressUpdate.emit(progress)
                    if ch.lower() == channel:
                        data = np.recfromcsv(file_, delimiter="\t")

                        labels = data['class__label']
                        probs = list()
                        for prob in data['class__probability']:
                            pstr = prob.strip('"').split(',')

                            # sanity check for class labels in the definition and
                            # the data file
                            lbs = [int(p.split(':')[0]) for p in pstr]
                            if set(classdef.class_names.keys()) != set(lbs):
                                msg = ("The labels in the class definition and "
                                       " the data files are inconsistent.\n%s, %s"
                                       %(str(lbs),
                                         str(classdef.class_names.keys())))
                                raise RuntimeError(msg)
                            probs.append(np.array([float(p.split(':')[1]) for p in pstr]))
                        probs = np.array(probs)

                        gfile = self._gallery_image(pos, matched.groupdict(),
                                                    channel)
                        dtable.add_track(labels, probs, pos, mappings[pos],
                                         gfile)

        if dtable.is_empty():
            raise RuntimeError("No data found for position '%s' and channel '%s' "
                               %(self.plate, channel))

        return dtable

    def interruption_point(self, message=None):
        if message is not None:
            prgs = ProgressMsg(meta=message)
            self.parent().progressUpdate.emit(prgs)
        QThread.currentThread().interruption_point()

    def __call__(self):
        self._makedirs()
        mappings = PlateMapping(self.positions)
        if self.ecopts.position_labels:
            mpfile = join(self.ecopts.mapping_dir, "%s.txt" %self.plate)
            mappings.read(mpfile)

        alldata = dict()
        for channel, cld in self.ecopts.class_definition.iteritems():
            dtable = self._load_data(mappings, channel, cld)
            msg = 'performing error correction on channel %s' %channel
            self.interruption_point(msg)

            # error correction
            hmm = Hmm(dtable, channel, cld, self.ecopts)
            data = hmm()
            alldata[channel] =  data

            # plotting and export
            report = HmmReport(data, self.ecopts, cld, self._hmm_dir)
            prefix = "%s_%s" %(channel.title(), self.ecopts.regionnames[channel])
            sby = self.ecopts.sortby.replace(" ", "_")

            self.interruption_point("plotting overview")
            report.overview(join(self._hmm_dir, '%s-%s.pdf' %(prefix, sby)))
            report.close_figures()

            self.interruption_point("plotting bar- and boxplots")
            report.bars_and_boxes(join(self._hmm_dir, '%s-%s_boxbars.pdf'
                                       %(prefix, sby)))
            report.close_figures()

            self.interruption_point("plotting hmm model")
            report.hmm_model(join(self._hmm_dir, "%s_%s_model.pdf")
                             %(prefix, sby))

            if self.ecopts.write_gallery:
                self.interruption_point("plotting image gallery")
                try:
                    # replace image_gallery_png with image_gallery_pdf
                    fn = join(self._gallery_dir,
                              '%s-%s_gallery.png' %(prefix, sby))
                    report.image_gallery_png(fn, self.ecopts.n_galleries,
                                             self.ecopts.resampling_factor)
                    report.close_figures()
                except Exception as e: # don't stop error corection
                    with open(join(self._gallery_dir, '%s-%s_error_readme.txt'
                                   %(prefix, sby)), 'w') as fp:
                        traceback.print_exc(file=fp)
                        fp.write("Check if gallery images exist!")
            report.export_hmm(join(self._hmm_dir, "%s-hmm.csv" %channel.title()), True)

        if self.ecopts.multichannel_galleries:
            fn = join(self._gallery_dir, 'MultiChannelGallery_%s.png'
                      %sby)
            self.interruption_point("plotting multichannel gallery")

            try:
                mcg = MultiChannelGallery(self.ecopts.class_definition, alldata,
                                          'primary', self.ecopts.n_galleries,
                                          self.ecopts.resampling_factor)
                mcg(fn, self.ecopts.regionnames.keys())
            # don't stop error correction
            except Exception as e:
                with open(join(self._gallery_dir, '%s-%s_error_readme.txt'
                               %(prefix, sby)), 'w') as fp:
                    traceback.print_exc(file=fp)
                    fp.write("Check if gallery images exist!")


if __name__ == "__main__":

    path_in = '/Users/hoefler/demo_data/ibb/mappings/input.txt'
    path_out = '/Users/hoefler/demo_data/ibb/mappings/output.txt'

    positons = ["018", "028", "051", "067"]
    pm = PlateMapping(positons)
    pm.read(path_in)
    pm['018']['OligoID'] = "just made up"
    pm.save(path_out)

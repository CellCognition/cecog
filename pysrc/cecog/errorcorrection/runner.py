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

from os.path import join, isfile, basename, dirname, splitext
from PyQt4 import QtCore
from PyQt4.QtCore import QThread

import cellh5

from cecog.util.util import makedirs
from cecog.threads.corethread import ProgressMsg
from cecog.errorcorrection.hmm import HmmSklearn
from cecog.errorcorrection.hmm import HmmTde

from cecog.errorcorrection import HmmReport
from cecog.errorcorrection import PlateMapping
from cecog.errorcorrection.datatable import HmmDataTable
from cecog.gallery import MultiChannelGallery
from cecog.learning.learning import ClassDefinition


class PlateRunner(QtCore.QObject):

    progressUpdate = QtCore.pyqtSignal(dict)

    def __init__(self, plates, outdirs, params_ec, *args, **kw):
        super(PlateRunner, self).__init__(*args, **kw)
        self.plates = plates
        self._outdirs = dict([(p, d) for p, d in zip(plates, outdirs)])
        self._is_aborted = False

        self.params_ec = params_ec

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

            ch5file = join(self._outdirs[plate], 'hdf5', "_all_positions.ch5")
            runner = PositionRunner(plate, self._outdirs[plate],
                                    self.params_ec, parent=self,
                                    ch5file=ch5file)
            runner()
            self.progressUpdate.emit(progress)


class PositionRunner(QtCore.QObject):

    def __init__(self, plate, outdir, ecopts, ch5file, parent=None,
                 *args, **kw):
        super(PositionRunner, self).__init__(parent, *args, **kw)
        self.ecopts = ecopts # error correction options
        self.plate = plate
        self._outdir = outdir

        self._channel_dirs = dict()
        self._makedirs()

        self.ch5file = ch5file
        self.files = glob.glob(dirname(ch5file)+"/*.ch5")
        self.files = [f for f in self.files if "_all_positions" not in f]

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

    def _load_classdef(self, region):
        classdef = ClassDefinition()
        try:
            ch5 = cellh5.CH5File(self.ch5file, "r")
            cld = ch5.class_definition(region)
        finally:
            ch5.close()
        classdef.load(cld)
        return classdef

    # XXX use contextlib to close file pointer
    def iterpos(self, ch5):
        """Iterate over (sub)positions in a linearized way"""
        for well, positions in ch5.positions.iteritems():
            for position in positions:
                yield ch5.get_position(well, position)

    def _load_data(self, mappings, channel):
        dtable = HmmDataTable()

        if isinstance(self.ecopts.regionnames[channel], tuple):
            chreg = "__".join((channel,
                               "-".join(self.ecopts.regionnames[channel])))
        else:
            chreg = "__".join((channel, self.ecopts.regionnames[channel]))


        progress = ProgressMsg(max=len(self.files))

        for file_ in self.files:
            position = splitext(basename(file_))[0]
            progress.meta = meta=("loading plate: %s, file: %s"
                                  %(self.plate, file_))
            progress.increment_progress()


            QThread.currentThread().interruption_point()
            self.parent().progressUpdate.emit(progress)
            QtCore.QCoreApplication.processEvents()

            ch5 = cellh5.CH5File(file_, "r")
            for pos in self.iterpos(ch5):
                if not pos.has_classification(chreg):
                    raise RuntimeError(("There is not classifier definition"
                                        "\nwell: %s, positin %s"
                                        %(pos.well, pos.pos)))

                objidx = np.array( \
                    pos.get_events(self.ecopts.ignore_tracking_branches),
                    dtype=int)
                tracks = pos.get_class_label(objidx, chreg)
                probs = pos.get_prediction_probabilities(objidx, chreg)
                objids = pos.get_object_table(chreg)[objidx]

                dtable.add_position(position, mappings[position])
                dtable.add_tracks(tracks, probs, position, mappings[position],
                                  objids)
            ch5.close()

        if dtable.is_empty():
            raise RuntimeError(
                "No data found for position '%s' and channel '%s' "
                %(self.plate, channel))
        return dtable, self._load_classdef(chreg)

    def interruption_point(self, message=None):
        if message is not None:
            prgs = ProgressMsg(meta=message)
            self.parent().progressUpdate.emit(prgs)
        QThread.currentThread().interruption_point()

    def __call__(self):
        self._makedirs()

        mappings = PlateMapping([splitext(basename(f))[0] for f in self.files])
        if self.ecopts.position_labels:
            mpfile = join(self.ecopts.mapping_dir, "%s.txt" %self.plate)
            mappings.read(mpfile)

        alldata = dict()
        for channel in self.ecopts.regionnames.keys():
            dtable, cld = self._load_data(mappings, channel)
            msg = 'performing error correction on channel %s' %channel
            self.interruption_point(msg)

            # error correction
            if self.ecopts.hmm_algorithm == self.ecopts.HMM_BAUMWELCH:
                hmm = HmmSklearn(dtable, channel, cld, self.ecopts)
            else:
                hmm = HmmTde(dtable, channel, cld, self.ecopts)

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
            report.hmm_model(join(self._hmm_dir, "%s-%s_model.pdf")
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

            report.export_hmm(join(self._hmm_dir, "%s-hmm.csv" %channel.title()),
                              self.ecopts.sortby)

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

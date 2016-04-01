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


__all__ = ('PlateMapping', 'PositionRunner', 'PlateRunner')


import os
import glob
import traceback
import numpy as np

from os.path import join, isfile, basename, dirname, splitext
from PyQt5 import QtCore
from PyQt5.QtCore import QThread

import cellh5

from cecog.io.hdf import Ch5File
from cecog.util.util import makedirs
from cecog.errorcorrection.hmm import HmmSklearn
from cecog.errorcorrection.hmm import HmmTde

from cecog.errorcorrection import HmmReport
from cecog.errorcorrection import PlateMapping
from cecog.errorcorrection.datatable import HmmDataTable
from cecog.classifier import ClassDefinition


class PlateRunner(QtCore.QObject):

    def __init__(self, plates, outdirs, params_ec, *args, **kw):
        super(PlateRunner, self).__init__(*args, **kw)
        self.plates = plates
        self._outdirs = dict([(p, d) for p, d in zip(plates, outdirs)])
        self._is_aborted = False

        self.params_ec = params_ec

    def abort(self):
        self._is_aborted = True

    def __call__(self):

        thread = QThread.currentThread()

        for i, plate in enumerate(self.plates):
            thread.interruption_point()
            ch5file = join(self._outdirs[plate], "%s.ch5" %plate)

            runner = PositionRunner(plate, self._outdirs[plate],
                                    self.params_ec, parent=self,
                                    ch5file=ch5file)
            runner()

            txt = ("Plate: '%s' (%d / %d)" %(plate, i+1, len(self.plates)))
            thread.statusUpdate(text=txt)


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
        self.files = glob.glob(join(dirname(ch5file), "cellh5", "*.ch5"))

    def _makedirs(self):
        """Create/setup output directories.

        -) <analyzed-dir>/analyzed (already exists)
        -) <analysis-dir>/hmm
        -) <analysis-dir>/hmm/gallery
        """
        assert isinstance(self._outdir, basestring)
        self._analyzed_dir = join(self._outdir, "analyzed")

        odirs = [join(self._outdir, "hmm")]
        if self.ecopts.write_gallery:
            odirs.append(join(self._outdir, "hmm", "gallery"))

        for odir in odirs:
            try:
                makedirs(odir)
            except os.error: # no permissions
                raise OSError("Missing permissions to create dir\n(%s)" %odir)
            else:
                setattr(self, "_%s_dir" %basename(odir.lower()).strip("_"), odir)

    def _load_classdef(self, region):

        with Ch5File(self.ch5file, mode="r") as ch5:
            cld = ch5.class_definition(region)
            classdef = ClassDefinition(cld)
        return classdef

    def _load_data(self, channel):

        dtable = HmmDataTable()

        # XXX read region names from hdf not from settings
        chreg = "%s__%s" %(channel, self.ecopts.regionnames[channel])

        # setup the progressbar correctly
        c = 3
        if self.ecopts.write_gallery:
            c = 4

        thread = QThread.currentThread()
        thread.statusUpdate(min=0, max=len(self.files) + c)

        with Ch5File(self.ch5file, mode="r") as ch5:
            layout = ch5.layout(self.plate)
            mappings = PlateMapping(layout)

            for pos in ch5.iter_positions():

                file_ = str(splitext(basename(pos.filename))[0])
                thread.statusUpdate(
                    text="loading plate: %s, file: %s" %(self.plate, file_))
                thread.increment.emit()
                thread.interruption_point()
                QtCore.QCoreApplication.processEvents()

                # only segmentation
                if not pos.has_classification(chreg):
                    continue

                # make dtable aware of all positions, sometime they contain
                # no tracks and I don't want to ignore them
                dtable.add_position(file_, mappings[file_])
                if not pos.has_events():
                    continue

                objidx = np.array( \
                    pos.get_events(not self.ecopts.ignore_tracking_branches),
                    dtype=int)
                tracks = pos.get_class_label(objidx, chreg)
                try:
                    probs = pos.get_prediction_probabilities(objidx, chreg)
                except KeyError as e:
                    probs = None

                grp_coord = cellh5.CH5GroupCoordinate( \
                    chreg, pos.pos, pos.well, pos.plate)
                dtable.add_tracks(tracks, file_, mappings[file_],
                                  objidx, grp_coord, probs)


        if dtable.is_empty():
            raise RuntimeError(
                "No data found for plate '%s' and channel '%s' "
                %(self.plate, channel))
        return dtable, self._load_classdef(chreg)

    def interruption_point(self, message=None, increment=False):
        thread = QThread.currentThread()
        if message is not None:
            thread.statusUpdate(meta=message, increment=increment)
        thread.interruption_point()

    def __call__(self):
        self._makedirs()

        for channel in self.ecopts.regionnames.keys():
            dtable, cld = self._load_data(channel)
            msg = 'performing error correction on channel %s' %channel
            self.interruption_point(msg)

            # error correction
            if self.ecopts.hmm_algorithm == self.ecopts.HMM_BAUMWELCH:
                hmm = HmmSklearn(dtable, channel, cld, self.ecopts)
            else:
                hmm = HmmTde(dtable, channel, cld, self.ecopts)

            data = hmm()

            # plots and export
            report = HmmReport(data, self.ecopts, cld, self._hmm_dir)
            prefix = "%s_%s" %(channel.title(), self.ecopts.regionnames[channel])
            sby = self.ecopts.sortby.replace(" ", "_")

            self.interruption_point("plotting overview", True)
            report.overview(join(self._hmm_dir, '%s-%s.pdf' %(prefix, sby)))
            report.close_figures()

            self.interruption_point("plotting bar- and boxplots", True)
            report.bars_and_boxes(join(self._hmm_dir, '%s-%s_boxbars.pdf'
                                       %(prefix, sby)))
            report.close_figures()

            self.interruption_point("plotting hmm model", True)
            report.hmm_model(join(self._hmm_dir, "%s-%s_model.pdf")
                             %(prefix, sby))


            if self.ecopts.write_gallery:
                self.interruption_point("plotting image gallery", True)
                try:
                    # replace image_gallery_png with image_gallery_pdf
                    fn = join(self._gallery_dir,
                              '%s-%s_gallery.png' %(prefix, sby))

                    with Ch5File(self.ch5file, mode='r') as ch5:
                        report.image_gallery_png(ch5, fn, self.ecopts.n_galleries,
                                                 self.ecopts.resampling_factor,
                                                 self.ecopts.size_gallery_image)
                        report.close_figures()
                except Exception as e: # don't stop error corection
                    with open(join(self._gallery_dir, '%s-%s_error_readme.txt'
                                   %(prefix, sby)), 'w') as fp:
                        traceback.print_exc(file=fp)
                        fp.write("Check if gallery images exist!")

            self.interruption_point("write data...", True)
            report.export_hmm(join(self._hmm_dir, "%s-%s_hmm.csv"
                                   %(prefix, sby)),
                              self.ecopts.sortby)


if __name__ == "__main__":

    path_in = '/Users/hoefler/demo_data/ibb/mappings/input.txt'
    path_out = '/Users/hoefler/demo_data/ibb/mappings/output.txt'

    positons = ["018", "028", "051", "067"]
    pm = PlateMapping(positons)
    pm.read(path_in)
    pm['018']['OligoID'] = "just made up"
    pm.save(path_out)

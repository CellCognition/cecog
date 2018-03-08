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

    def _load_classdef(self, mask):

        with Ch5File(self.ch5file, mode="r") as ch5:
            cld = ch5.classDefinition(mask)
            classdef = ClassDefinition(cld)
        return classdef

    def _load_data(self, channel):

        dtable = HmmDataTable()

        # XXX read region names from hdf not from settings
        mask = "%s__%s" %(channel, self.ecopts.regionnames[channel])

        c = 2
        if self.ecopts.write_gallery:
            c += 1

        thread = QThread.currentThread()

        with Ch5File(self.ch5file, mode="r") as ch5:
            layout = ch5.layout(self.plate)
            mappings = PlateMapping(layout)
            thread.statusUpdate(min=0, max=ch5.numberSites(self.plate) + c)

            for site in ch5.iterSites():

                ws = "%s_%02d" %(site.well, int(site.site))
                thread.statusUpdate(
                    text="loading plate: %s, file: %s" %(site.plate, ws))
                thread.increment.emit()
                thread.interruption_point()
                QtCore.QCoreApplication.processEvents()

                if not ch5.hasClassifier(mask):
                    continue

                # make dtable aware of all positions, sometime they contain
                # no tracks and I don't want to ignore them
                dtable.add_position(ws, mappings[ws])
                if not ch5.hasEvents(site):
                    continue

                objidx = ch5.events(site, self.ecopts.ignore_tracking_branches)
                tracks = np.asarray(ch5.predictions(site, mask))[objidx]

                try:
                    probs = ch5.probabilities(site, mask)[objidx, :]
                except KeyError as e:
                    probs = None

                site.mask = mask
                dtable.add_tracks(tracks, ws, mappings[ws],
                                  objidx, site, probs)

        if dtable.is_empty():
            raise RuntimeError(
                "No data found for plate '%s' and channel '%s' "
                %(self.plate, channel))
        return dtable, self._load_classdef(mask)

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

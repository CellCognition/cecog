"""
pyhmm.py
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
import csv
import glob
import numpy as np
from collections import OrderedDict

from os.path import join, isfile, isdir, basename
from PyQt4 import QtCore

from cecog.util.util import makedirs
from cecog.threads.corethread import ProgressMsg
from cecog.learning.learning import ClassDefinition
from cecog.export.regexp import re_events
from cecog.errorcorrection.datatable import HmmDataTable

class PlateMapping(OrderedDict):
    """Read/Write plate mappings files. Default for all positions is None.
    After reading, all values are set according to the file."""


    POSITION = 'Position'
    WELL = 'Well'
    SITE = 'Site'
    ROW = 'Row'
    COLUMN = 'Column'
    GENE = 'Gene Symbol'
    OLIGO = 'OligoId'
    GROUP = 'Group'

    _colnames = [POSITION, WELL, SITE, ROW, COLUMN, GENE, OLIGO, GROUP]

    def __init__(self, positions):
        super(PlateMapping, self).__init__()
        for pos in positions:
            self.setdefault(pos, None)

    def read(self, filename):
        if not isfile(filename):
            raise IOError("Plate mapping file not found\n(%s)" %filename)

        with open(filename, "r") as fp:
            reader = csv.DictReader(fp, delimiter='\t')
            for line in reader:
                pos = line['Position']
                del line['Position']
                self[pos] = line

    def save(self, filename, mode="w"):
        with open(filename, mode=mode) as fp:
            writer = csv.DictWriter(fp, fieldnames=self._colnames,
                                    delimiter='\t')
            writer.writeheader()
            for k, v in self.iteritems():
                line = v.copy()
                line.update({"Position": k})
                writer.writerow(line)


class PlateRunner(QtCore.QObject):

    # check if signal works with dict
    progressUpdate = QtCore.pyqtSignal('PyQt_PyObject')

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

    def load_class_definitions(self, classifier_directories,
                               filename='class_definition.txt'):
        class_definitions = dict()
        for channel, clfdir in classifier_directories.iteritems():
            class_definitions[channel] = ClassDefinition(join(clfdir, filename))
            class_definitions[channel].load()
        return class_definitions

    def __call__(self):
        if self.params_ec.position_labels:
            self._check_mapping_files()

        progress = ProgressMsg(max=len(self.plates), meta="Error correction...")
        classdef = self.load_class_definitions(self.params_ec.classifier_dirs)

        for i, plate in enumerate(self.plates):
            if self._is_aborted:
                break
            else:
                progress.text = "Plate: '%s' (%d / %d)" \
                    %(plate, i+1, len(self.plates))
                self.progressUpdate.emit(progress)
                # self._imagecontainer.set_plate(plate)
                runner = PositionRunner(plate, self._outdirs[plate],
                                        self.params_ec, classdef)
                runner()
                progress.progress  = i + 1
                self.progressUpdate.emit(progress)


class PositionRunner(QtCore.QObject):

    def __init__(self, plate, outdir, ecopts, class_definition,
                 positions=None, *args, **kw):
        super(PositionRunner, self).__init__(*args, **kw)
        self.ecopts = ecopts # error correction options
        self.plate = plate
        self._outdir = outdir
        self.class_definition = class_definition

        self._channel_dirs = dict()
        self._makedirs()

        self.positions = positions
        if positions is None:
            self.positions = self._listdirs(self._analyzed_dir)

    def _listdirs(self, path):
        return [x for x in os.listdir(path)
                if isdir(join(path, x)) and not x.startswith('_')]

    def _makedirs(self):
        """Create/setup output directories.

        -) <analyzed-dir>/analyzed (already exists)
        -) <analysis-dir>/hmm
        -) <analysis-dir>/hmm/<channel-region>
        """
        assert isinstance(self._outdir, basestring)
        self._analyzed_dir = join(self._outdir, "analyzed")

        odirs = (join(self._outdir, "hmm"),)
        for odir in odirs:
            try:
                makedirs(odir)
            except os.error: # no permissions
                raise OSError("Missing permissions to create dir\n(%s)" %odir)
            else:
                setattr(self, "_%s_dir" %basename(odir.lower()).strip("_"), odir)
        for channel, region in self.ecopts.regionnames.iteritems():
            chdir = "%s-%s" %(channel, region)
            self._channel_dirs[channel] = join(self._hmm_dir, chdir)
            try:
                makedirs(self._channel_dirs[channel])
            except os.error:
                raise OSError("Missing permissions to create dir\n(%s)"
                              %self._channels_dir[channel])

    def _load_data(self, mappings, channel, class_definition):
        dtable = HmmDataTable()
        for pos in self.positions:
            files = glob.glob(join(self._analyzed_dir, pos, 'statistics',
                                   'events')+os.sep+"*.txt")

            for file_ in files:
                matched = re_events.match(basename(file_))
                try:
                    ch = matched.group('channel')
                except AttributeError:
                    pass
                else:
                    if ch.lower() == channel:
                        data = np.recfromcsv(file_, delimiter="\t")

                        labels = data['class__label']
                        probs = list()
                        for prob in data['class__probability']:
                            probs.append(np.array([float(p.split(':')[1]) \
                               for p in prob.strip('"').split(',')]))
                        probs = np.array(probs)
                        dtable.add_track(labels, probs, pos, mappings[pos])
        import pdb; pdb.set_trace()

    def __call__(self):
        self._makedirs()
        mappings = PlateMapping(self.positions)
        if self.ecopts.position_labels:
            mpfile = join(self.ecopts.mapping_dir, "%s.txt" %self.plate)
            mappings.read(mpfile)

        for channel, cld in self.class_definition.iteritems():
            self._load_data(mappings, channel, cld)

if __name__ == "__main__":

    path_in = '/Users/hoefler/demo_data/ibb/mappings/input.txt'
    path_out = '/Users/hoefler/demo_data/ibb/mappings/output.txt'

    positons = ["018", "028", "051", "067"]
    pm = PlateMapping(positons)
    pm.read(path_in)
    pm['018']['OligoID'] = "just made up"
    pm.save(path_out)
